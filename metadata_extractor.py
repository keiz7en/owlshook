#!/usr/bin/env python3

import os
import sys
import json
import struct
import subprocess
import tempfile
import re
from pathlib import Path
from urllib.parse import urlparse

try:
    import urllib.request
    import urllib.error
    import ssl
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'GIF8': 'image/gif',
    b'RIFF': 'video/webm',
    b'\x00\x00\x00': 'video/mp4',
    b'\x1a\x45\xdf\xa3': 'video/mkv',
}

GPS_TAGS = {
    0x0001: 'GPSLatitudeRef',
    0x0002: 'GPSLatitude',
    0x0003: 'GPSLongitudeRef',
    0x0004: 'GPSLongitude',
    0x0005: 'GPSAltitudeRef',
    0x0006: 'GPSAltitude',
    0x0007: 'GPSTimeStamp',
    0x001d: 'GPSDateStamp',
}

IFD_TAGS = {
    0x010f: 'Make',
    0x0110: 'Model',
    0x0112: 'Orientation',
    0x011a: 'XResolution',
    0x011b: 'YResolution',
    0x0131: 'Software',
    0x0132: 'DateTime',
    0x013b: 'Artist',
    0x8298: 'Copyright',
    0x8769: 'ExifIFD',
    0x8825: 'GPSInfo',
}


def detect_file_type(filepath):
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
        for magic, filetype in MAGIC_BYTES.items():
            if header.startswith(magic):
                return filetype
    except Exception:
        pass
    return None


def read_exif_short(data, offset, endian):
    fmt = '>H' if endian == 'big' else '<H'
    return struct.unpack_from(fmt, data, offset)[0]


def read_exif_long(data, offset, endian):
    fmt = '>I' if endian == 'big' else '<I'
    return struct.unpack_from(fmt, data, offset)[0]


def read_exif_rational(data, offset, endian):
    num = read_exif_long(data, offset, endian)
    den = read_exif_long(data, offset + 4, endian)
    return num / den if den else 0


def parse_exif(filepath):
    results = {}
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        if not data.startswith(b'\xff\xd8\xff'):
            return results

        offset = 2
        if data[offset:offset+2] != b'\xe1':
            return results
        offset += 2

        tiff_offset = offset + 6
        if data[tiff_offset:tiff_offset+2] == b'II':
            endian = 'little'
        elif data[tiff_offset:tiff_offset+2] == b'MM':
            endian = 'big'
        else:
            return results

        ifd_offset = read_exif_long(data, tiff_offset + 4, endian)

        def parse_ifd(ifd_off, tag_dict=None):
            if tag_dict is None:
                tag_dict = IFD_TAGS
            entries = read_exif_short(data, ifd_off, endian)
            result = {}
            for i in range(entries):
                entry_off = ifd_off + 2 + (i * 12)
                tag = read_exif_short(data, entry_off, endian)
                typ = read_exif_short(data, entry_off + 2, endian)
                count = read_exif_long(data, entry_off + 4, endian)
                val_off = entry_off + 8

                if tag in tag_dict:
                    tag_name = tag_dict[tag]
                    if typ == 3 and count == 1:
                        result[tag_name] = read_exif_short(data, val_off, endian)
                    elif typ == 4 and count == 1:
                        result[tag_name] = read_exif_long(data, val_off, endian)
                    elif typ == 5:
                        result[tag_name] = read_exif_rational(data, val_off, endian)
                    elif typ == 2:
                        max_len = min(count, 1000)
                        if count > 4:
                            str_off = read_exif_long(data, val_off, endian)
                            result[tag_name] = data[str_off:str_off+max_len].rstrip(b'\x00').decode('ascii', errors='ignore')
                        else:
                            result[tag_name] = data[val_off:val_off+count].rstrip(b'\x00').decode('ascii', errors='ignore')
                    elif typ == 3 and count > 1:
                        values = []
                        for j in range(count):
                            values.append(read_exif_short(data, val_off + (j * 2), endian))
                        result[tag_name] = values
                    elif typ == 4 and count > 1:
                        values = []
                        for j in range(count):
                            values.append(read_exif_long(data, val_off + (j * 4), endian))
                        result[tag_name] = values
                elif tag == 0x8769:
                    exif_ifd_off = read_exif_long(data, val_off, endian)
                    result['ExifData'] = parse_ifd(exif_ifd_off, IFD_TAGS)
                elif tag == 0x8825:
                    gps_ifd_off = read_exif_long(data, val_off, endian)
                    result['GPSInfo'] = parse_ifd(gps_ifd_off, GPS_TAGS)
            return result

        results = parse_ifd(ifd_offset)
        return results
    except Exception as e:
        return {'error': str(e)}


def dms_to_decimal(dms, ref):
    if isinstance(dms, list) and len(dms) >= 3:
        d = dms[0]
        m = dms[1]
        s = dms[2]
        decimal = d + (m / 60) + (s / 3600)
        if ref in ('S', 'W'):
            decimal = -decimal
        return round(decimal, 6)
    return None


def extract_gps_info(exif_data):
    gps = exif_data.get('GPSInfo', {})
    if not gps:
        return None

    lat = gps.get('GPSLatitude')
    lat_ref = gps.get('GPSLatitudeRef', 'N')
    lon = gps.get('GPSLongitude')
    lon_ref = gps.get('GPSLongitudeRef', 'E')

    if lat and lon:
        lat_dec = dms_to_decimal(lat, lat_ref)
        lon_dec = dms_to_decimal(lon, lon_ref)
        if lat_dec is not None and lon_dec is not None:
            return {
                'latitude': lat_dec,
                'longitude': lon_dec,
                'google_maps': f'https://www.google.com/maps?q={lat_dec},{lon_dec}',
                'altitude': gps.get('GPSAltitude'),
                'timestamp': gps.get('GPSTimeStamp'),
                'datestamp': gps.get('GPSDateStamp'),
            }
    return None


def run_exiftool(filepath):
    try:
        result = subprocess.run(
            ['exiftool', '-json', '-GPS:all', '-DateTimeOriginal', '-CreateDate', '-Make', '-Model', '-Software', filepath],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def extract_basic_info(filepath):
    info = {
        'filename': os.path.basename(filepath),
        'filesize': os.path.getsize(filepath),
        'filetype': detect_file_type(filepath),
    }
    try:
        stat = os.stat(filepath)
        info['modified'] = str(stat.st_mtime)
    except Exception:
        pass
    return info


def analyze_file(filepath):
    if not os.path.exists(filepath):
        return {'error': 'File not found'}

    result = extract_basic_info(filepath)
    exif_data = parse_exif(filepath)

    if exif_data and 'error' not in exif_data:
        result['exif'] = exif_data
        gps = extract_gps_info(exif_data)
        if gps:
            result['location'] = gps
    else:
        tool_data = run_exiftool(filepath)
        if tool_data and len(tool_data) > 0:
            result['exif'] = tool_data[0]
            if 'GPSLatitude' in tool_data[0] and 'GPSLongitude' in tool_data[0]:
                lat = tool_data[0].get('GPSLatitude', 0)
                lon = tool_data[0].get('GPSLongitude', 0)
                lat_ref = tool_data[0].get('GPSLatitudeRef', 'N')
                lon_ref = tool_data[0].get('GPSLongitudeRef', 'E')
                if lat_ref == 'S':
                    lat = -lat
                if lon_ref == 'W':
                    lon = -lon
                result['location'] = {
                    'latitude': round(lat, 6),
                    'longitude': round(lon, 6),
                    'google_maps': f'https://www.google.com/maps?q={round(lat, 6)},{round(lon, 6)}',
                }

    return result


def scan_directory(dirpath, extensions=None):
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.mp4', '.avi', '.mov', '.mkv']

    results = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            if Path(file).suffix.lower() in extensions:
                filepath = os.path.join(root, file)
                data = analyze_file(filepath)
                if data.get('location'):
                    results.append(data)
    return results


def download_from_url(url, timeout=30):
    if not HAS_URLLIB:
        return None, "urllib not available"
    
    temp_dir = tempfile.mkdtemp(prefix='metadata_')
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if not filename or '.' not in filename:
        filename = 'downloaded_file'
    filepath = os.path.join(temp_dir, filename)
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        req.add_header('Accept', 'image/webp,image/apng,image/*,*/*;q=0.8')
        
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            with open(filepath, 'wb') as f:
                f.write(response.read())
        
        return filepath, None
    except Exception as e:
        return None, str(e)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_or_directory_or_url>")
        print(f"Example: {sys.argv[0]} photo.jpg")
        print(f"Example: {sys.argv[0]} /path/to/photos/")
        print(f"Example: {sys.argv[0]} https://instagram.com/p/ABC123/")
        sys.exit(1)

    target = sys.argv[1]
    is_url = target.startswith('http://') or target.startswith('https://')
    
    if is_url:
        print(f"Downloading from: {target}")
        filepath, error = download_from_url(target)
        if error:
            print(f"Download failed: {error}")
            sys.exit(1)
        print(f"Downloaded to: {filepath}")
        result = analyze_file(filepath)
        result['source_url'] = target
        print(json.dumps(result, indent=2, default=str))
        try:
            os.remove(filepath)
            os.rmdir(os.path.dirname(filepath))
        except:
            pass
    elif os.path.isfile(target):
        result = analyze_file(target)
        print(json.dumps(result, indent=2, default=str))
    elif os.path.isdir(target):
        results = scan_directory(target)
        if results:
            print(json.dumps(results, indent=2, default=str))
        else:
            print("No files with location data found.")
    else:
        print("Invalid path or URL.")
        sys.exit(1)


if __name__ == '__main__':
    main()
