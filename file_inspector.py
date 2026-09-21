#!/usr/bin/env python3

import os
import sys
import json
import hashlib
import struct
import subprocess
import datetime
from pathlib import Path

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
WHITE = '\033[97m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

def supports_color():
    if not hasattr(sys.stdout, 'isatty'):
        return False
    if not sys.stdout.isatty():
        return False
    return True

USE_COLOR = supports_color()

if not USE_COLOR:
    RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = BOLD = DIM = RESET = ''

MAGIC_SIGNATURES = {
    b'\xff\xd8\xff': ('JPEG Image', '.jpg'),
    b'\x89PNG': ('PNG Image', '.png'),
    b'GIF87a': ('GIF Image', '.gif'),
    b'GIF89a': ('GIF Image', '.gif'),
    b'BM': ('BMP Image', '.bmp'),
    b'II\x2a\x00': ('TIFF Image', '.tiff'),
    b'MM\x00\x2a': ('TIFF Image', '.tiff'),
    b'%PDF': ('PDF Document', '.pdf'),
    b'PK\x03\x04': ('ZIP Archive', '.zip'),
    b'PK\x05\x06': ('ZIP Archive', '.zip'),
    b'\x1f\x8b': ('GZIP Archive', '.gz'),
    b'BZh': ('BZIP2 Archive', '.bz2'),
    b'\xfd7zXZ': ('XZ Archive', '.xz'),
    b'7z\xbc\xaf\x27\x1c': ('7-Zip Archive', '.7z'),
    b'Rar!\x1a\x07': ('RAR Archive', '.rar'),
    b'\x00\x00\x01\x00': ('ICO Image', '.ico'),
    b'\x00\x00\x02\x00': ('CUR Image', '.cur'),
    b'RIFF': ('RIFF Container', '.wav'),
    b'ID3': ('MP3 Audio', '.mp3'),
    b'\xff\xfb': ('MP3 Audio', '.mp3'),
    b'\xff\xf3': ('MP3 Audio', '.mp3'),
    b'\xff\xf2': ('MP3 Audio', '.mp3'),
    b'OggS': ('OGG Audio', '.ogg'),
    b'fLaC': ('FLAC Audio', '.flac'),
    b'\x1a\x45\xdf\xa3': ('MKV Video', '.mkv'),
    b'\x00\x00\x00\x18ftyp': ('MP4 Video', '.mp4'),
    b'\x00\x00\x00\x1cftyp': ('MP4 Video', '.mp4'),
    b'\x00\x00\x00\x20ftyp': ('MP4 Video', '.mp4'),
    b'\x00\x00\x00\x14ftyp': ('MP4 Video', '.mp4'),
    b'\x00\x00\x00\x10ftyp': ('MP4 Video', '.mp4'),
    b'\x00\x00\x00ftyp': ('MP4 Video', '.mp4'),
    b'\x52\x49\x46\x46': ('RIFF Container', '.avi'),
    b'\x4d\x54\x68\x64': ('MIDI Audio', '.mid'),
    b'MSCF': ('Compound Document', '.doc'),
    b'\xd0\xcf\x11\xe0': ('OLE Document', '.xls'),
    b'<!DOCTYPE': ('HTML Document', '.html'),
    b'<html': ('HTML Document', '.html'),
    b'<?xml': ('XML Document', '.xml'),
    b'{\n': ('JSON File', '.json'),
    b'{\r\n': ('JSON File', '.json'),
    b'[': ('JSON File', '.json'),
    b'#!/bin/bash': ('Shell Script', '.sh'),
    b'#!/bin/sh': ('Shell Script', '.sh'),
    b'#!/usr/bin/env python': ('Python Script', '.py'),
    b'\xef\xbb\xbf': ('UTF-8 BOM Text', '.txt'),
}


def get_file_hashes(filepath):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
        return {
            'md5': md5.hexdigest(),
            'sha1': sha1.hexdigest(),
            'sha256': sha256.hexdigest()
        }
    except Exception:
        return {'md5': '', 'sha1': '', 'sha256': ''}


def detect_file_type(filepath):
    try:
        with open(filepath, 'rb') as f:
            header = f.read(32)
        for magic, (name, ext) in MAGIC_SIGNATURES.items():
            if header.startswith(magic):
                return {'type': name, 'extension': ext}
    except Exception:
        pass
    return {'type': 'Unknown', 'extension': ''}


def get_file_timestamps(filepath):
    result = {}
    try:
        stat = os.stat(filepath)
        result['created'] = datetime.datetime.fromtimestamp(stat.st_ctime).isoformat()
        result['modified'] = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        result['accessed'] = datetime.datetime.fromtimestamp(stat.st_atime).isoformat()
        if hasattr(stat, 'st_birthtime'):
            result['birthtime'] = datetime.datetime.fromtimestamp(stat.st_birthtime).isoformat()
    except Exception:
        pass
    return result


def get_exif_data(filepath):
    result = {}
    try:
        proc = subprocess.run(
            ['exiftool', '-json', '-G', filepath],
            capture_output=True, text=True, timeout=30
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            if data and len(data) > 0:
                result = data[0]
    except FileNotFoundError:
        try:
            proc = subprocess.run(
                ['python3', '-c', f'import exifread; f=open("{filepath}","rb"); tags=exifread.process_file(f); print(dict(tags))'],
                capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                result = {'ExifRead': proc.stdout.strip()}
        except Exception:
            pass
    except Exception:
        pass
    return result


def get_pdf_metadata(filepath):
    result = {}
    try:
        with open(filepath, 'rb') as f:
            content = f.read(10000)
        if b'%PDF' in content[:10]:
            result['is_pdf'] = True
            try:
                proc = subprocess.run(
                    ['exiftool', '-json', filepath],
                    capture_output=True, text=True, timeout=30
                )
                if proc.returncode == 0:
                    data = json.loads(proc.stdout)
                    if data:
                        result.update(data[0])
            except Exception:
                pass
    except Exception:
        pass
    return result


def get_office_metadata(filepath):
    result = {}
    ext = Path(filepath).suffix.lower()
    try:
        proc = subprocess.run(
            ['exiftool', '-json', filepath],
            capture_output=True, text=True, timeout=30
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            if data:
                result = data[0]
    except Exception:
        pass
    return result


def parse_gps_str(val, ref):
    try:
        if isinstance(val, str):
            import re
            match = re.match(r"(\d+)\s*deg\s+(\d+)'\s+([\d.]+)\"", val)
            if match:
                d = float(match.group(1))
                m = float(match.group(2))
                s = float(match.group(3))
                dec = d + (m / 60.0) + (s / 3600.0)
                ref_upper = ref.upper()
                if ref_upper in ('S', 'W', 'SOUTH', 'WEST'):
                    dec = -dec
                return round(dec, 6)
        elif isinstance(val, (list, tuple)) and len(val) >= 3:
            d = float(val[0])
            m = float(val[1])
            s = float(val[2])
            dec = d + (m / 60.0) + (s / 3600.0)
            ref_upper = ref.upper()
            if ref_upper in ('S', 'W', 'SOUTH', 'WEST'):
                dec = -dec
            return round(dec, 6)
    except:
        pass
    return None


def get_video_metadata(filepath):
    result = {}
    try:
        proc = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath],
            capture_output=True, text=True, timeout=30
        )
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
    except FileNotFoundError:
        try:
            proc = subprocess.run(
                ['exiftool', '-json', filepath],
                capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                if data:
                    result = data[0]
        except Exception:
            pass
    except Exception:
        pass
    return result


def get_audio_metadata(filepath):
    result = {}
    try:
        proc = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
            capture_output=True, text=True, timeout=30
        )
        if proc.returncode == 0:
            result = json.loads(proc.stdout)
    except FileNotFoundError:
        try:
            proc = subprocess.run(
                ['exiftool', '-json', filepath],
                capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                if data:
                    result = data[0]
        except Exception:
            pass
    except Exception:
        pass
    return result


def extract_embedded_strings(filepath, min_length=4):
    result = []
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        current = []
        for byte in content:
            if 32 <= byte <= 126:
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    result.append(''.join(current))
                current = []
        if len(current) >= min_length:
            result.append(''.join(current))
    except Exception:
        pass
    return result[:100]


def find_urls(strings):
    urls = []
    for s in strings:
        if 'http://' in s or 'https://' in s or 'www.' in s:
            urls.append(s)
    return urls


def find_emails(strings):
    emails = []
    for s in strings:
        parts = s.split()
        for part in parts:
            if '@' in part and '.' in part:
                if part.replace('@', '').replace('.', '').isalnum():
                    emails.append(part)
    return emails


def find_ip_addresses(strings):
    ips = []
    for s in strings:
        parts = s.replace(',', ' ').replace(';', ' ').split()
        for part in parts:
            if '.' in part:
                nums = part.split('.')
                if len(nums) == 4:
                    try:
                        if all(0 <= int(n) <= 255 for n in nums):
                            ips.append(part)
                    except ValueError:
                        pass
    return ips


def find_file_paths(strings):
    paths = []
    for s in strings:
        if 'C:\\' in s or '/home/' in s or '/Users/' in s or '/tmp/' in s:
            paths.append(s)
    return paths


def find_usernames(strings):
    users = []
    for s in strings:
        if 'user' in s.lower() or 'admin' in s.lower() or 'login' in s.lower():
            users.append(s)
    return users


def find_software_info(strings):
    software = []
    for s in strings:
        if any(x in s.lower() for x in ['photoshop', 'gimp', 'lightroom', 'premiere', 'final cut', 'word', 'excel', 'powerpoint', 'chrome', 'firefox', 'safari']):
            software.append(s)
    return software


def analyze_file(filepath):
    if not os.path.exists(filepath):
        return {'error': 'File not found'}

    result = {
        'file': filepath,
        'filename': os.path.basename(filepath),
        'filesize': os.path.getsize(filepath),
        'filesize_human': f"{os.path.getsize(filepath) / 1024:.2f} KB" if os.path.getsize(filepath) < 1024*1024 else f"{os.path.getsize(filepath) / (1024*1024):.2f} MB",
    }

    file_type = detect_file_type(filepath)
    result['file_type'] = file_type['type']
    result['detected_extension'] = file_type['extension']

    result['timestamps'] = get_file_timestamps(filepath)

    result['hashes'] = get_file_hashes(filepath)

    strings = extract_embedded_strings(filepath)
    if strings:
        result['embedded_strings'] = {
            'total_count': len(strings),
            'sample': strings[:20],
            'urls': find_urls(strings),
            'emails': find_emails(strings),
            'ip_addresses': find_ip_addresses(strings),
            'file_paths': find_file_paths(strings),
            'usernames': find_usernames(strings),
            'software_info': find_software_info(strings),
        }

    ext = Path(filepath).suffix.lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.raw', '.cr2', '.nef', '.arw'):
        exif = get_exif_data(filepath)
        if exif:
            result['exif'] = exif
            gps_data = {}
            for key, val in exif.items():
                if 'gps' in key.lower():
                    gps_data[key] = val
            if gps_data:
                result['gps'] = gps_data
            
            lat_val = None
            lat_ref = None
            lon_val = None
            lon_ref = None
            for key in exif:
                k = str(key).lower()
                if 'gpslatitude' in k and 'ref' not in k:
                    lat_val = exif[key]
                elif 'gpslatituderef' in k:
                    lat_ref = str(exif[key]).strip()
                elif 'gpslongitude' in k and 'ref' not in k:
                    lon_val = exif[key]
                elif 'gpslongituderef' in k:
                    lon_ref = str(exif[key]).strip()
            
            if lat_val and lon_val:
                lat_dec = parse_gps_str(lat_val, lat_ref or 'N')
                lon_dec = parse_gps_str(lon_val, lon_ref or 'E')
                if lat_dec is not None and lon_dec is not None:
                    result['google_maps'] = f"https://maps.google.com/?q={lat_dec},{lon_dec}"
                    result['latitude'] = lat_dec
                    result['longitude'] = lon_dec

    elif ext == '.pdf':
        result['pdf_metadata'] = get_pdf_metadata(filepath)

    elif ext in ('.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp'):
        result['office_metadata'] = get_office_metadata(filepath)

    elif ext in ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'):
        result['video_metadata'] = get_video_metadata(filepath)

    elif ext in ('.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'):
        result['audio_metadata'] = get_audio_metadata(filepath)

    try:
        proc = subprocess.run(
            ['file', filepath],
            capture_output=True, text=True, timeout=10
        )
        if proc.returncode == 0:
            result['file_command'] = proc.stdout.strip()
    except Exception:
        pass

    return result


def scan_directory(dirpath, recursive=True):
    results = []
    if recursive:
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    data = analyze_file(filepath)
                    results.append(data)
                except Exception:
                    pass
    else:
        for item in os.listdir(dirpath):
            filepath = os.path.join(dirpath, item)
            if os.path.isfile(filepath):
                try:
                    data = analyze_file(filepath)
                    results.append(data)
                except Exception:
                    pass
    return results


def print_result(result):
    print(f"{CYAN}{'=' * 70}{RESET}")
    print(f"{BOLD}{WHITE}FILE: {result.get('filename', 'Unknown')}{RESET}")
    print(f"{CYAN}{'=' * 70}{RESET}")
    print(f"  {GREEN}Path            {RESET}: {result.get('file', '')}")
    print(f"  {GREEN}File Size       {RESET}: {result.get('filesize_human', '')}")
    print(f"  {GREEN}File Type       {RESET}: {result.get('file_type', '')}")
    print(f"  {GREEN}Detected Ext    {RESET}: {result.get('detected_extension', '')}")

    if 'timestamps' in result:
        ts = result['timestamps']
        print(f"  {GREEN}Created         {RESET}: {ts.get('created', 'N/A')}")
        print(f"  {GREEN}Modified        {RESET}: {ts.get('modified', 'N/A')}")
        print(f"  {GREEN}Accessed        {RESET}: {ts.get('accessed', 'N/A')}")
        if 'birthtime' in ts:
            print(f"  {GREEN}Birth Time      {RESET}: {ts.get('birthtime', 'N/A')}")

    if 'hashes' in result:
        h = result['hashes']
        print(f"  {GREEN}MD5             {RESET}: {h.get('md5', '')}")
        print(f"  {GREEN}SHA-1           {RESET}: {h.get('sha1', '')}")
        print(f"  {GREEN}SHA-256         {RESET}: {h.get('sha256', '')}")

    if 'file_command' in result:
        print(f"  {GREEN}File Command    {RESET}: {result.get('file_command', '')}")

    if 'gps' in result:
        print(f"\n  {BOLD}{YELLOW}--- GPS LOCATION ---{RESET}")
        gps = result['gps']
        for key, val in gps.items():
            print(f"  {YELLOW}{key:18}{RESET}: {val}")
        if 'google_maps' in result:
            print(f"\n  {YELLOW}Google Maps     {RESET}: {result['google_maps']}")
        if 'latitude' in result and 'longitude' in result:
            print(f"  {YELLOW}Coordinates     {RESET}: {result['latitude']}, {result['longitude']}")
    elif 'latitude' in result and 'longitude' in result:
        print(f"\n  {BOLD}{YELLOW}*** LOCATION FOUND ***{RESET}")
        print(f"  {YELLOW}Latitude{RESET}  : {result['latitude']}")
        print(f"  {YELLOW}Longitude{RESET} : {result['longitude']}")
        print(f"  {YELLOW}Maps{RESET}      : {result.get('google_maps', '')}")
    else:
        print(f"\n  {DIM}[i] No GPS location (often removed by social media){RESET}")

    if 'exif' in result:
        print(f"\n  {BOLD}{WHITE}--- EXIF DATA ---{RESET}")
        for key, val in result['exif'].items():
            if 'thumbnail' not in key.lower() and 'sourcefile' not in key.lower():
                print(f"  {GREEN}{key:30}{RESET}: {val}")
                if 'FBMD' in str(val):
                    fbmd = str(val).replace('FBMD', '')
                    print(f"  {GREEN}{'  -> FBMD decoded':30}{RESET}: {fbmd[:100]}...")

    if 'embedded_strings' in result:
        es = result['embedded_strings']
        if es.get('urls'):
            print(f"\n  {BOLD}{WHITE}--- URLS FOUND ({len(es['urls'])}) ---{RESET}")
            for url in es['urls'][:10]:
                print(f"  {CYAN}{url}{RESET}")
        if es.get('emails'):
            print(f"\n  {BOLD}{WHITE}--- EMAILS FOUND ({len(es['emails'])}) ---{RESET}")
            for email in es['emails'][:10]:
                print(f"  {CYAN}{email}{RESET}")
        if es.get('ip_addresses'):
            print(f"\n  {BOLD}{WHITE}--- IP ADDRESSES FOUND ({len(es['ip_addresses'])}) ---{RESET}")
            for ip in es['ip_addresses'][:10]:
                print(f"  {CYAN}{ip}{RESET}")
        if es.get('file_paths'):
            print(f"\n  {BOLD}{WHITE}--- FILE PATHS FOUND ({len(es['file_paths'])}) ---{RESET}")
            for path in es['file_paths'][:10]:
                print(f"  {CYAN}{path}{RESET}")
        if es.get('software_info'):
            print(f"\n  {BOLD}{WHITE}--- SOFTWARE INFO ---{RESET}")
            for sw in es['software_info'][:10]:
                print(f"  {CYAN}{sw}{RESET}")

    print()


def download_url(url, timeout=30):
    import tempfile
    import subprocess
    from urllib.parse import urlparse
    tmp = tempfile.mkdtemp()
    name = os.path.basename(urlparse(url).path).split('?')[0]
    if '.' not in name:
        name = 'downloaded.jpg'
    fpath = os.path.join(tmp, name)
    try:
        result = subprocess.run([
            'curl', '-sk', '-L',
            '-o', fpath,
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '-H', 'Accept: image/webp,image/apng,image/*,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Referer: https://www.facebook.com/',
            '-H', 'sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120"',
            '-H', 'sec-ch-ua-mobile: ?0',
            '-H', 'sec-ch-ua-platform: "Windows"',
            '-H', 'Sec-Fetch-Dest: image',
            '-H', 'Sec-Fetch-Mode: no-cors',
            '-H', 'Sec-Fetch-Site: cross-site',
            '--max-time', '30',
            url
        ], capture_output=True, text=True, timeout=35)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 100:
            return fpath
    except Exception as e:
        print(f"  curl error: {e}")
    try:
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        req.add_header('Accept', 'image/webp,image/apng,image/*,*/*;q=0.8')
        req.add_header('Referer', 'https://www.facebook.com/')
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            data = r.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        if os.path.getsize(fpath) > 100:
            return fpath
    except Exception as e:
        print(f"  urllib error: {e}")
    return None


def main():
    if len(sys.argv) < 2:
        print(f"{BOLD}{CYAN}Usage:{RESET} {sys.argv[0]} <file_or_directory_or_url> [output.json]")
        print()
        print(f"{GREEN}Commands:{RESET}")
        print(f"  {DIM}{sys.argv[0]} photo.jpg{RESET}")
        print(f"  {DIM}{sys.argv[0]} document.pdf{RESET}")
        print(f"  {DIM}{sys.argv[0]} /path/to/folder/{RESET}")
        print(f"  {DIM}{sys.argv[0]} https://facebook.com/photo.php?fbid=123{RESET}")
        print(f"  {DIM}{sys.argv[0]} https://instagram.com/p/ABC123/{RESET}")
        print(f"  {DIM}{sys.argv[0]} suspect.mp4 output.json{RESET}")
        print()
        print(f"  {DIM}Part of OwlsHook Forensic Toolkit{RESET}")
        print()
        sys.exit(1)

    target = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    is_url = target.startswith('http://') or target.startswith('https://')

    if is_url:
        print(f"\n  {GREEN}Downloading:{RESET} {target}")
        fpath = download_url(target)
        if fpath:
            print(f"  {GREEN}Downloaded:{RESET} {fpath}")
            result = analyze_file(fpath)
            result['source_url'] = target
            print_result(result)
            try:
                os.remove(fpath)
                os.rmdir(os.path.dirname(fpath))
            except:
                pass
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"  {GREEN}Report saved to {output_file}{RESET}")
        else:
            print(f"  {RED}Download failed!{RESET}")
            sys.exit(1)

    elif os.path.isfile(target):
        result = analyze_file(target)
        print_result(result)
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"  {GREEN}Report saved to {output_file}{RESET}")

    elif os.path.isdir(target):
        print(f"\n  {GREEN}Scanning directory:{RESET} {target}")
        print()
        results = scan_directory(target)
        for r in results:
            print_result(r)
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"  {GREEN}Report saved to {output_file}{RESET}")
        else:
            json_output = target.rstrip('/').replace('/', '_') + '_report.json'
            with open(json_output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"  {GREEN}Report saved to {json_output}{RESET}")

    else:
        print(f"  {RED}Invalid path or URL.{RESET}")
        sys.exit(1)


if __name__ == '__main__':
    main()
