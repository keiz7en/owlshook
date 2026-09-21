#!/usr/bin/env python3

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import re
from datetime import datetime
from urllib.parse import urlparse

try:
    import urllib.request
    import ssl
except:
    pass

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


def get_hash(fpath):
    h = hashlib.md5()
    s = hashlib.sha256()
    try:
        with open(fpath, 'rb') as f:
            while True:
                d = f.read(8192)
                if not d:
                    break
                h.update(d)
                s.update(d)
        return h.hexdigest(), s.hexdigest()
    except:
        return '', ''


def get_exif(fpath):
    try:
        p = subprocess.run(
            ['exiftool', '-json', '-GPS*', '-DateTimeOriginal', '-CreateDate',
             '-ModifyDate', '-Make', '-Model', '-Software', '-Artist',
             '-Copyright', '-ImageWidth', '-ImageHeight', '-FileSize',
             '-FilePermissions', '-FileName', '-Directory', '-Description',
             '-ImageDescription', '-Title', '-Subject', '-Keywords',
             '-Location', '-City', '-State', '-Country', '-SubLocation',
             '-GPSLatitude', '-GPSLongitude', '-GPSLatitudeRef', '-GPSLongitudeRef',
             fpath],
            capture_output=True, text=True, timeout=30
        )
        if p.returncode == 0:
            data = json.loads(p.stdout)
            if data:
                return data[0]
    except:
        pass
    return {}


def dms_to_dec(dms, ref):
    try:
        if hasattr(dms, 'values'):
            vals = dms.values
            d = float(vals[0].num) / vals[0].den
            m = float(vals[1].num) / vals[1].den
            s = float(vals[2].num) / vals[2].den
        elif isinstance(dms, (list, tuple)) and len(dms) >= 3:
            d = float(dms[0])
            m = float(dms[1])
            s = float(dms[2])
        else:
            return None
        dec = d + (m / 60.0) + (s / 3600.0)
        if ref in ('S', 'W', 's', 'w'):
            dec = -dec
        return round(dec, 6)
    except:
        return None


def get_gps(info):
    lat_val = None
    lat_ref = None
    lon_val = None
    lon_ref = None
    
    for key in info:
        k = str(key).lower()
        if 'gpslatitude' in k and 'ref' not in k:
            lat_val = info[key]
        elif 'gpslatituderef' in k:
            lat_ref = str(info[key]).strip()
        elif 'gpslongitude' in k and 'ref' not in k:
            lon_val = info[key]
        elif 'gpslongituderef' in k:
            lon_ref = str(info[key]).strip()
    
    if lat_val and lon_val:
        lat_dec = parse_gps_coord(lat_val, lat_ref or 'N')
        lon_dec = parse_gps_coord(lon_val, lon_ref or 'E')
        if lat_dec is not None and lon_dec is not None:
            maps = f"https://maps.google.com/?q={lat_dec},{lon_dec}"
            return lat_dec, lon_dec, maps
    
    return None, None, None


def parse_gps_coord(val, ref):
    try:
        if hasattr(val, 'values'):
            vals = val.values
            d = float(vals[0].num) / vals[0].den
            m = float(vals[1].num) / vals[1].den
            s = float(vals[2].num) / vals[2].den
        elif isinstance(val, str):
            import re
            match = re.match(r"(\d+)\s*deg\s+(\d+)'\s+([\d.]+)\"", val)
            if match:
                d = float(match.group(1))
                m = float(match.group(2))
                s = float(match.group(3))
            else:
                return None
        elif isinstance(val, (list, tuple)) and len(val) >= 3:
            d = float(val[0])
            m = float(val[1])
            s = float(val[2])
        else:
            return None
        dec = d + (m / 60.0) + (s / 3600.0)
        ref_upper = ref.upper()
        if ref_upper in ('S', 'W', 'SOUTH', 'WEST'):
            dec = -dec
        return round(dec, 6)
    except:
        return None


def get_file_info(fpath):
    info = {}
    try:
        st = os.stat(fpath)
        info['name'] = os.path.basename(fpath)
        info['size'] = st.st_size
        info['created'] = datetime.fromtimestamp(st.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        info['modified'] = datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        info['accessed'] = datetime.fromtimestamp(st.st_atime).strftime('%Y-%m-%d %H:%M:%S')
        md5, sha256 = get_hash(fpath)
        info['md5'] = md5
        info['sha256'] = sha256
    except:
        pass
    return info


def get_file_type(fpath):
    try:
        with open(fpath, 'rb') as f:
            h = f.read(32)
        if h[:3] == b'\xff\xd8\xff':
            return 'JPEG'
        if h[:4] == b'\x89PNG':
            return 'PNG'
        if h[:4] == b'GIF8':
            return 'GIF'
        if h[:4] == b'BM':
            return 'BMP'
        if h[:2] == b'II' or h[:2] == b'MM':
            return 'TIFF'
        if h[:4] == b'%PDF':
            return 'PDF'
        if h[:4] == b'RIFF':
            return 'AVI/WEBP'
        if b'ftyp' in h[:12]:
            return 'MP4/MOV'
        if h[:4] == b'\x1a\x45\xdf\xa3':
            return 'MKV'
        if h[:3] == b'ID3' or h[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
            return 'MP3'
        if h[:4] == b'fLaC':
            return 'FLAC'
        if h[:4] == b'OggS':
            return 'OGG'
    except:
        pass
    return 'UNKNOWN'


def download(url):
    try:
        import subprocess
        tmp = tempfile.mkdtemp()
        real_url = resolve_url(url)
        name = os.path.basename(urlparse(real_url).path).split('?')[0]
        if '.' not in name:
            name = 'image.jpg'
        fpath = os.path.join(tmp, name)
        referer = f'{urlparse(real_url).scheme}://{urlparse(real_url).netloc}/'
        
        if 'google_drive' in get_platform(url):
            file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if not file_id_match:
                file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
            if file_id_match:
                file_id = file_id_match.group(1)
                download_url = f'https://drive.google.com/uc?export=download&id={file_id}&confirm=t'
                
                result = subprocess.run([
                    'curl', '-sk', '-L',
                    '-o', fpath,
                    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    '-H', 'Accept: image/*,*/*;q=0.8',
                    '-H', 'Referer: https://drive.google.com/',
                    '--max-time', '30',
                    download_url
                ], capture_output=True, text=True, timeout=35)
                
                if os.path.exists(fpath) and os.path.getsize(fpath) > 100:
                    with open(fpath, 'rb') as f:
                        header = f.read(200)
                    if b'<!DOCTYPE' in header or b'<html' in header or b'<head' in header:
                        os.remove(fpath)
                        return None
                    return fpath
                return None
        else:
            result = subprocess.run([
                'curl', '-sk', '-L',
                '-o', fpath,
                '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '-H', 'Accept: image/webp,image/apng,image/*,*/*;q=0.8',
                '-H', f'Referer: {referer}',
                '--max-time', '30',
                real_url
            ], capture_output=True, text=True, timeout=35)
            
            if os.path.exists(fpath) and os.path.getsize(fpath) > 100:
                return fpath
        
        if os.path.exists(fpath):
            os.remove(fpath)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(real_url)
        req.add_header('User-Agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        req.add_header('Accept', 'image/*,*/*;q=0.8')
        req.add_header('Referer', referer)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            with open(fpath, 'wb') as f:
                f.write(r.read())
        if os.path.getsize(fpath) < 100:
            os.remove(fpath)
            os.rmdir(tmp)
            return None
        return fpath
    except:
        return None


def resolve_url(url):
    platform = get_platform(url)
    if platform == 'google_drive':
        try:
            file_id = None
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
            else:
                match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
                if match:
                    file_id = match.group(1)
            if file_id:
                return f'https://drive.google.com/uc?export=download&id={file_id}&confirm=t'
            match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
            if match:
                folder_id = match.group(1)
                return f'https://drive.google.com/drive/folders/{folder_id}'
        except:
            pass
    if platform == 'googleusercontent':
        if '=w' in url or '-k-' in url:
            base_url = url.split('=')[0]
            return base_url
    if platform == 'wikimedia':
        try:
            if '/wiki/' in url:
                page_title = url.split('/wiki/')[-1]
                api_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}'
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(api_url)
                req.add_header('User-Agent', 'OwlsHook/2.0')
                with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                    data = json.loads(r.read().decode('utf-8'))
                if 'thumbnail' in data and 'source' in data['thumbnail']:
                    return data['thumbnail']['source']
        except:
            pass
    if platform in ('reddit',):
        try:
            json_url = url.rstrip('/') + '.json'
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(json_url)
            req.add_header('User-Agent',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                data = json.loads(r.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0:
                post = data[0]['data']['children'][0]['data']
                if 'preview' in post and 'images' in post['preview']:
                    return post['preview']['images'][0]['source']['url'].replace('&amp;', '&')
                if 'url' in post:
                    return post['url']
        except:
            pass
    if platform in ('twitter',):
        if '/photo/' in url:
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url)
                req.add_header('User-Agent',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                    html = r.read().decode('utf-8', errors='ignore')
                imgs = re.findall(r'(https?://pbs\.twimg\.com/media/[^\"]+)', html)
                if imgs:
                    return imgs[0]
            except:
                pass
    if platform in ('facebook',) and 'fbcdn' not in url:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url)
            req.add_header('User-Agent',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                html = r.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'(https?://scontent[^"\']+?\.(?:jpg|jpeg|png|webp))', html)
            if imgs:
                return imgs[0]
            imgs = re.findall(r'"uri":"(https?://[^"]+?\.(?:jpg|jpeg|png|webp)[^"]*)"', html)
            if imgs:
                return imgs[0].replace('&amp;', '&')
        except:
            pass
    if platform in ('instagram',) and 'cdninstagram' not in url:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url)
            req.add_header('User-Agent',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                html = r.read().decode('utf-8', errors='ignore')
            imgs = re.findall(r'(https?://[^"\']*cdninstagram[^"\']+?\.(?:jpg|jpeg|png|webp))', html)
            if imgs:
                return imgs[0]
        except:
            pass
    return url


def cleanup(fpath):
    try:
        d = os.path.dirname(fpath)
        os.remove(fpath)
        os.rmdir(d)
    except:
        pass


def find_location(info):
    lat, lon, maps = get_gps(info)
    if lat and lon:
        return lat, lon, maps

    text_fields = ['Description', 'ImageDescription', 'Title', 'Subject',
                   'Keywords', 'Artist', 'Copyright', 'Location', 'City',
                   'State', 'Country', 'SubLocation']
    
    for field in text_fields:
        if field in info:
            val = str(info[field])
            location_keywords = ['university', 'college', 'school', 'hospital',
                                'church', 'mosque', 'temple', 'bank', 'hotel',
                                'restaurant', 'cafe', 'park', 'market', 'mall',
                                'airport', 'station', 'bridge', 'tower', 'stadium',
                                'dubai', 'daka', 'dhaka', 'chittagong', 'sylhet',
                                'bangladesh', 'india', 'pakistan', 'usa', 'uk',
                                'canada', 'australia', 'germany', 'france', 'japan',
                                'china', 'russia', 'brazil', 'mexico', 'nigeria']
            
            val_lower = val.lower()
            for keyword in location_keywords:
                if keyword in val_lower:
                    return None, None, val

    return None, None, None


def analyze(fpath, url=None):
    result = {}
    if url:
        result['source_url'] = url
        result['platform'] = get_platform(url)
    fi = get_file_info(fpath)
    result.update(fi)
    result['file_type'] = get_file_type(fpath)
    exif = get_exif(fpath)
    if exif:
        result['exif'] = exif
        lat, lon, maps = find_location(exif)
        if lat and lon:
            result['location'] = {
                'latitude': lat,
                'longitude': lon,
                'google_maps': maps
            }
        elif maps and not lat:
            result['text_location'] = maps
    if url and 'location' not in result and 'text_location' not in result:
        server_geo = get_server_geolocation(url)
        if server_geo:
            result['server_location'] = server_geo
    ai_result = detect_ai_content(fpath, exif)
    if ai_result:
        result['ai_analysis'] = ai_result
    video_result = get_video_metadata(fpath)
    if video_result:
        result['video_metadata'] = video_result
    tz_result = analyze_timezone(exif)
    if tz_result:
        result['timezone_analysis'] = tz_result
    try:
        p = subprocess.run(['file', fpath], capture_output=True, text=True, timeout=10)
        if p.returncode == 0:
            result['file_info'] = p.stdout.strip()
    except:
        pass
    return result


def detect_ai_content(fpath, exif=None):
    try:
        indicators = {
            'ai_generated': False,
            'confidence': 'low',
            'signs': []
        }
        ai_keywords = [
            'dall-e', 'dalle', 'midjourney', 'stable diffusion', 'flux',
            'craiyon', 'nightcafe', 'dreamstudio', 'leonardo', 'runway',
            'sora', 'pika', 'kling', 'hailuo', 'minimax', 'luma',
            'deepfake', 'synthetic', 'generated', 'ai art', 'neural',
            'artbreeder', 'deepai', 'openai', 'anthropic', 'google ai',
            'meta ai', 'adobe firefly', 'canva ai', 'photoshop ai'
        ]
        if exif:
            for key, val in exif.items():
                val_str = str(val).lower()
                for kw in ai_keywords:
                    if kw in val_str:
                        indicators['ai_generated'] = True
                        indicators['signs'].append(f"EXIF contains '{kw}' in {key}")
            software = str(exif.get('Software', '')).lower()
            artist = str(exif.get('Artist', '')).lower()
            description = str(exif.get('Description', '')).lower()
            for source in [software, artist, description]:
                for kw in ai_keywords:
                    if kw in source:
                        indicators['ai_generated'] = True
                        indicators['signs'].append(f"Found '{kw}' in metadata")
        try:
            with open(fpath, 'rb') as f:
                header = f.read(10000)
            text_content = header.decode('utf-8', errors='ignore').lower()
            for kw in ai_keywords:
                if kw in text_content:
                    indicators['signs'].append(f"Found '{kw}' in file header")
        except:
            pass
        try:
            p = subprocess.run(['strings', fpath], capture_output=True, text=True, timeout=10)
            if p.returncode == 0:
                strings_out = p.stdout.lower()
                for kw in ai_keywords:
                    if kw in strings_out:
                        if f"Found '{kw}' in file header" not in indicators['signs']:
                            indicators['signs'].append(f"Found '{kw}' in strings")
                        indicators['ai_generated'] = True
        except:
            pass
        if exif:
            make = str(exif.get('Make', '')).lower()
            model = str(exif.get('Model', '')).lower()
            software = str(exif.get('Software', '')).lower()
            if 'canon' in make or 'nikon' in make or 'sony' in make or 'fuji' in make:
                indicators['signs'].append("Camera manufacturer detected (likely real)")
            if 'adobe' in software and 'photoshop' in software:
                indicators['signs'].append("Adobe Photoshop detected (may be edited)")
            if 'gimp' in software:
                indicators['signs'].append("GIMP detected (may be edited)")
        if indicators['ai_generated']:
            indicators['confidence'] = 'high' if len(indicators['signs']) >= 2 else 'medium'
        return indicators
    except:
        return None


def get_video_metadata(filepath):
    try:
        ext = os.path.splitext(filepath)[1].lower()
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv',
                      '.m4v', '.3gp', '.ts', '.mts', '.vob']
        if ext not in video_exts:
            return None
        result = {}
        try:
            p = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_format', '-show_streams', filepath],
                capture_output=True, text=True, timeout=30
            )
            if p.returncode == 0:
                data = json.loads(p.stdout)
                if 'format' in data:
                    fmt = data['format']
                    result['duration'] = fmt.get('duration', 'N/A')
                    result['size'] = fmt.get('size', 'N/A')
                    result['bitrate'] = fmt.get('bit_rate', 'N/A')
                    result['format_name'] = fmt.get('format_name', 'N/A')
                    if 'tags' in fmt:
                        for key, val in fmt['tags'].items():
                            if key.lower() in ['location', 'creation_time', 'artist',
                                              'comment', 'description', 'title']:
                                result[f'video_{key}'] = val
                if 'streams' in data:
                    for stream in data['streams']:
                        if stream.get('codec_type') == 'video':
                            result['video_codec'] = stream.get('codec_name', 'N/A')
                            result['resolution'] = f"{stream.get('width', '?')}x{stream.get('height', '?')}"
                            result['fps'] = stream.get('r_frame_rate', 'N/A')
                            result['video_codec'] = stream.get('codec_name', 'N/A')
                        elif stream.get('codec_type') == 'audio':
                            result['audio_codec'] = stream.get('codec_name', 'N/A')
                            result['sample_rate'] = stream.get('sample_rate', 'N/A')
        except FileNotFoundError:
            pass
        try:
            p = subprocess.run(
                ['exiftool', '-json', '-GPS*', '-DateTimeOriginal', '-CreateDate',
                 '-Make', '-Model', '-Software', '-Artist', '-Description',
                 '-ImageWidth', '-ImageHeight', '-Duration', '-VideoCodec',
                 '-AudioCodec', '-Location', '-City', '-Country', filepath],
                capture_output=True, text=True, timeout=30
            )
            if p.returncode == 0:
                data = json.loads(p.stdout)
                if data:
                    for key, val in data[0].items():
                        if key not in result:
                            result[key] = val
        except:
            pass
        return result if result else None
    except:
        return None


def analyze_timezone(exif):
    try:
        result = {}
        gps_time = None
        gps_offset = None
        exif_time = None
        if exif:
            gps_dt = exif.get('GPSDateTime') or exif.get('GPSTimeStamp') or exif.get('GPSDateStamp')
            if gps_dt:
                gps_time = str(gps_dt)
                result['gps_time'] = gps_time
            exif_dt = exif.get('DateTimeOriginal') or exif.get('CreateDate') or exif.get('ModifyDate')
            if exif_dt:
                exif_time = str(exif_dt)
            gps_lat = exif.get('GPSLatitude')
            gps_lon = exif.get('GPSLongitude')
            gps_lat_ref = exif.get('GPSLatitudeRef', 'N')
            gps_lon_ref = exif.get('GPSLongitudeRef', 'E')
            if gps_lat and gps_lon:
                try:
                    lat = None
                    lon = None
                    if isinstance(gps_lat, (int, float)):
                        lat = float(gps_lat)
                    elif isinstance(gps_lat, str):
                        import re
                        match = re.match(r"(\d+)\s*deg\s+(\d+)'\s+([\d.]+)\"", gps_lat)
                        if match:
                            d = float(match.group(1))
                            m = float(match.group(2))
                            s = float(match.group(3))
                            lat = d + (m / 60.0) + (s / 3600.0)
                            if str(gps_lat_ref).upper() in ('S', 'SOUTH'):
                                lat = -lat
                    if isinstance(gps_lon, (int, float)):
                        lon = float(gps_lon)
                    elif isinstance(gps_lon, str):
                        import re
                        match = re.match(r"(\d+)\s*deg\s+(\d+)'\s+([\d.]+)\"", gps_lon)
                        if match:
                            d = float(match.group(1))
                            m = float(match.group(2))
                            s = float(match.group(3))
                            lon = d + (m / 60.0) + (s / 3600.0)
                            if str(gps_lon_ref).upper() in ('W', 'WEST'):
                                lon = -lon
                    if lat is not None and lon is not None:
                        offset_hours = round(lon / 15.0)
                        gps_offset = f"+{offset_hours}" if offset_hours >= 0 else str(offset_hours)
                        result['gps_timezone'] = f"UTC{gps_offset}"
                        result['gps_timezone_hint'] = f"Approximate timezone from GPS coordinates"
                except:
                    pass
        if exif_time:
            try:
                from datetime import datetime
                time_str = exif_time.replace(':', '-', 2)
                if '+' in time_str:
                    dt = datetime.fromisoformat(time_str)
                elif '-' in time_str[10:]:
                    dt = datetime.fromisoformat(time_str)
                else:
                    dt = datetime.strptime(exif_time, '%Y:%m:%d %H:%M:%S')
                result['upload_time_utc'] = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                tz_regions = {
                    '-12': ['Baker Island'], '-11': ['American Samoa', 'Midway'],
                    '-10': ['Hawaii', 'French Polynesia'], '-9': ['Alaska', 'Juneau'],
                    '-8': ['California', 'Vancouver', 'Los Angeles', 'San Francisco', 'Seattle'],
                    '-7': ['Denver', 'Phoenix', 'Calgary'], '-6': ['Chicago', 'Mexico City', 'Dallas'],
                    '-5': ['New York', 'Toronto', 'Miami', 'Bogota', 'Lima'],
                    '-4': ['Santiago', 'Halifax', 'Caracas'], '-3': ['Buenos Aires', 'Sao Paulo'],
                    '-2': ['South Georgia'], '-1': ['Azores', 'Cape Verde'],
                    '0': ['London', 'Lisbon', 'Accra', 'Reykjavik'],
                    '1': ['Paris', 'Berlin', 'Rome', 'Lagos', 'Algiers'],
                    '2': ['Cairo', 'Athens', 'Helsinki', 'Johannesburg'],
                    '3': ['Moscow', 'Istanbul', 'Nairobi', 'Riyadh', 'Dhaka'],
                    '4': ['Dubai', 'Baku', 'Tbilisi'],
                    '5': ['Karachi', 'Tashkent', 'Yekaterinburg'],
                    '5:30': ['Mumbai', 'Delhi', 'Kolkata', 'Chennai', 'Bangalore'],
                    '6': ['Dhaka', 'Almaty', 'Omsk'],
                    '6:30': ['Yangon'],
                    '7': ['Bangkok', 'Jakarta', 'Hanoi', 'Krasnoyarsk'],
                    '8': ['Beijing', 'Singapore', 'Perth', 'Hong Kong', 'Kuala Lumpur'],
                    '9': ['Tokyo', 'Seoul', 'Pyongyang'],
                    '9:30': ['Adelaide', 'Darwin'],
                    '10': ['Sydney', 'Melbourne', 'Vladivostok', 'Guam'],
                    '11': ['Solomon Islands', 'New Caledonia'],
                    '12': ['Auckland', 'Fiji', 'Kamchatka'],
                }
                offset_str = gps_offset if gps_offset else '0'
                if offset_str in tz_regions:
                    result['possible_regions'] = tz_regions[offset_str]
                result['upload_time_local'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        return result if result else None
    except:
        return None


def get_server_geolocation(url):
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None
        ip = None
        try:
            import socket
            ip = socket.gethostbyname(hostname)
        except:
            return None
        if not ip:
            return None
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            req = urllib.request.Request(f'http://ip-api.com/json/{ip}')
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                data = json.loads(r.read().decode('utf-8'))
            if data.get('status') == 'success':
                return {
                    'server_ip': ip,
                    'server_city': data.get('city', 'Unknown'),
                    'server_region': data.get('regionName', 'Unknown'),
                    'server_country': data.get('country', 'Unknown'),
                    'server_country_code': data.get('countryCode', ''),
                    'server_org': data.get('org', 'Unknown'),
                    'server_isp': data.get('isp', 'Unknown'),
                    'server_maps': f"https://maps.google.com/?q={data.get('lat', 0)},{data.get('lon', 0)}",
                    'server_lat': data.get('lat', 0),
                    'server_lon': data.get('lon', 0)
                }
        except:
            pass
        try:
            req = urllib.request.Request(f'https://ipinfo.io/{ip}/json')
            req.add_header('User-Agent', 'OwlsHook/2.0')
            with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                data = json.loads(r.read().decode('utf-8'))
            if 'loc' in data:
                lat, lon = data['loc'].split(',')
                return {
                    'server_ip': ip,
                    'server_city': data.get('city', 'Unknown'),
                    'server_region': data.get('region', 'Unknown'),
                    'server_country': data.get('country', 'Unknown'),
                    'server_org': data.get('org', 'Unknown'),
                    'server_maps': f"https://maps.google.com/?q={lat},{lon}",
                    'server_lat': float(lat),
                    'server_lon': float(lon)
                }
        except:
            pass
    except:
        pass
    return None


def get_platform(url):
    u = url.lower()
    if 'instagram' in u:
        return 'instagram'
    if 'facebook' in u or 'fbcdn' in u:
        return 'facebook'
    if 'twitter' in u or 'x.com' in u or 'twimg' in u:
        return 'twitter'
    if 'reddit' in u or 'redd.it' in u:
        return 'reddit'
    if 'imgur' in u:
        return 'imgur'
    if 'youtube' in u or 'youtu.be' in u:
        return 'youtube'
    if 'linkedin' in u or 'licdn' in u:
        return 'linkedin'
    if 'tiktok' in u:
        return 'tiktok'
    if 'snapchat' in u:
        return 'snapchat'
    if 't.me' in u or 'telegram' in u:
        return 'telegram'
    if 'whatsapp' in u:
        return 'whatsapp'
    if 'unsplash' in u:
        return 'unsplash'
    if 'pexels' in u:
        return 'pexels'
    if 'pixabay' in u:
        return 'pixabay'
    if 'flickr' in u:
        return 'flickr'
    if 'drive.google' in u:
        return 'google_drive'
    if 'photos.google' in u or 'picasaweb' in u:
        return 'google_photos'
    if 'maps.google' in u or 'goo.gl/maps' in u:
        return 'google_maps'
    if 'lh3.googleusercontent' in u or 'lh4.googleusercontent' in u or 'lh5.googleusercontent' in u:
        return 'googleusercontent'
    if 'google' in u or 'gstatic' in u:
        return 'google'
    if 'pinimg' in u or 'pinterest' in u:
        return 'pinterest'
    if 'tumblr' in u:
        return 'tumblr'
    if 'deviantart' in u:
        return 'deviantart'
    if 'fbsbx' in u or 'fbcdn' in u:
        return 'facebook_cdn'
    if 'cdninstagram' in u:
        return 'instagram_cdn'
    if 'dropbox' in u:
        return 'dropbox'
    if 'onedrive' in u:
        return 'onedrive'
    if 'icloud' in u:
        return 'icloud'
    if 'mega.nz' in u or 'mega.co' in u:
        return 'mega'
    if 'mediafire' in u:
        return 'mediafire'
    if 'archive.org' in u:
        return 'archive'
    if 'wikimedia' in u or 'wikipedia' in u:
        return 'wikimedia'
    return 'unknown'


def show(r):
    print('')
    print(f"{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{WHITE}  FILE: {r.get('name', 'Unknown')}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}")

    if 'source_url' in r:
        print(f"  {GREEN}Source{RESET}    : {r['source_url']}")
        print(f"  {GREEN}Platform{RESET}  : {r.get('platform', 'N/A')}")

    if 'page_title' in r:
        print(f"  {GREEN}Title{RESET}     : {r['page_title'][:80]}")
    if 'og_title' in r:
        print(f"  {GREEN}OG Title{RESET}  : {r['og_title'][:80]}")
    if 'og_description' in r:
        print(f"  {GREEN}Desc{RESET}      : {r['og_description'][:100]}")
    if 'author' in r:
        print(f"  {GREEN}Author{RESET}    : {r['author']}")
    if 'post_date' in r:
        print(f"  {GREEN}Post Date{RESET} : {r['post_date']}")
    if 'file_name' in r:
        print(f"  {GREEN}File Name{RESET} : {r['file_name']}")
    if 'file_size' in r:
        print(f"  {GREEN}File Size{RESET} : {r['file_size']}")
    if 'mime_type' in r:
        print(f"  {GREEN}MIME Type{RESET} : {r['mime_type']}")
    if 'created' in r:
        print(f"  {GREEN}Created{RESET}   : {r['created']}")
    if 'modified' in r:
        print(f"  {GREEN}Modified{RESET}  : {r['modified']}")

    print(f"  {GREEN}Type{RESET}      : {r.get('file_type', 'N/A')}")
    print(f"  {GREEN}Size{RESET}      : {r.get('size', 0)} bytes")
    if 'md5' in r:
        print(f"  {GREEN}MD5{RESET}       : {r.get('md5', 'N/A')}")
    if 'sha256' in r:
        print(f"  {GREEN}SHA-256{RESET}   : {r.get('sha256', 'N/A')}")

    if 'location' in r:
        loc = r['location']
        print('')
        print(f"  {BOLD}{GREEN}✅ REAL GPS LOCATION FOUND ✅{RESET}")
        print(f"  {GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {GREEN}✓ This is REAL GPS from the photo metadata{RESET}")
        print(f"  {GREEN}✓ Coordinates where photo was ACTUALLY taken{RESET}")
        print(f"  {GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {YELLOW}Latitude{RESET}  : {loc['latitude']}")
        print(f"  {YELLOW}Longitude{RESET} : {loc['longitude']}")
        print(f"  {YELLOW}Maps{RESET}      : {loc['google_maps']}")
    elif 'text_location' in r:
        print('')
        print(f"  {BOLD}{YELLOW}📍 LOCATION FOUND (from EXIF text) ⚠️{RESET}")
        print(f"  {YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {YELLOW}⚠ Location from description/metadata text{RESET}")
        print(f"  {YELLOW}⚠ May not be exact - verify with other sources{RESET}")
        print(f"  {YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {YELLOW}Location{RESET}  : {r['text_location']}")
    elif 'server_location' in r:
        srv = r['server_location']
        print('')
        print(f"  {BOLD}{RED}⚠️  WARNING: SERVER LOCATION ONLY ⚠️{RESET}")
        print(f"  {RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {RED}⚠ This is NOT the real photo location!{RESET}")
        print(f"  {RED}⚠ This is WHERE THE SERVER IS, not the photographer{RESET}")
        print(f"  {RED}⚠ Social media strips real GPS - this is just the server{RESET}")
        print(f"  {RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {YELLOW}Server IP{RESET}    : {srv.get('server_ip', 'N/A')}")
        print(f"  {YELLOW}Server City{RESET}  : {srv.get('server_city', 'N/A')}")
        print(f"  {YELLOW}Server Region{RESET}: {srv.get('server_region', 'N/A')}")
        print(f"  {YELLOW}Server Country{RESET}: {srv.get('server_country', 'N/A')}")
        if 'server_org' in srv:
            print(f"  {YELLOW}Organization{RESET} : {srv['server_org']}")
        if 'server_isp' in srv:
            print(f"  {YELLOW}ISP{RESET}        : {srv['server_isp']}")
        print(f"  {YELLOW}Server Maps{RESET}  : {srv.get('server_maps', 'N/A')}")
        print(f"  {RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {DIM}💡 Tip: Server location ≠ Photo location{RESET}")
        print(f"  {DIM}💡 Example: Server in Germany, photo taken in USA{RESET}")
        print(f"  {DIM}💡 Use EXIF GPS or visual analysis for real location{RESET}")
    else:
        print('')
        print(f"  {DIM}[i] No GPS location (often removed by social media){RESET}")

    if 'exif' in r:
        ex = r['exif']
        has_data = False
        for k, v in ex.items():
            if 'thumbnail' not in k.lower() and 'sourcefile' not in k.lower():
                if not has_data:
                    print('')
                    print(f"  {BOLD}{WHITE}--- EXIF ---{RESET}")
                    has_data = True
                print(f"  {GREEN}{k:14}{RESET}: {v}")
                if 'FBMD' in str(v):
                    fbmd = str(v).replace('FBMD', '')
                    print(f"  {GREEN}FBMD data{RESET}   : {fbmd}")

    if 'file_info' in r:
        print(f"\n  {GREEN}File Info{RESET}  : {r['file_info']}")

    if 'ai_analysis' in r:
        ai = r['ai_analysis']
        print('')
        print(f"  {BOLD}{MAGENTA}--- AI ANALYSIS ---{RESET}")
        if ai.get('ai_generated'):
            print(f"  {RED}⚠ AI GENERATED: YES{RESET}")
            print(f"  {RED}Confidence: {ai.get('confidence', 'N/A').upper()}{RESET}")
        else:
            print(f"  {GREEN}✓ AI GENERATED: NO{RESET}")
            print(f"  {GREEN}Likely real human content{RESET}")
        if ai.get('signs'):
            print(f"  {DIM}Detection signs:{RESET}")
            for sign in ai['signs']:
                print(f"    {DIM}• {sign}{RESET}")

    if 'video_metadata' in r:
        vid = r['video_metadata']
        print('')
        print(f"  {BOLD}{CYAN}--- VIDEO METADATA ---{RESET}")
        if 'duration' in vid:
            try:
                dur = float(vid['duration'])
                mins = int(dur // 60)
                secs = int(dur % 60)
                print(f"  {CYAN}Duration{RESET}    : {mins}m {secs}s")
            except:
                print(f"  {CYAN}Duration{RESET}    : {vid['duration']}")
        if 'resolution' in vid:
            print(f"  {CYAN}Resolution{RESET}  : {vid['resolution']}")
        if 'video_codec' in vid:
            print(f"  {CYAN}Video Codec{RESET} : {vid['video_codec']}")
        if 'audio_codec' in vid:
            print(f"  {CYAN}Audio Codec{RESET} : {vid['audio_codec']}")
        if 'fps' in vid:
            print(f"  {CYAN}FPS{RESET}         : {vid['fps']}")
        if 'bitrate' in vid:
            print(f"  {CYAN}Bitrate{RESET}    : {vid['bitrate']}")
        for key in ['video_location', 'video_creation_time', 'video_artist',
                     'video_Description', 'video_comment']:
            if key in vid:
                nice_key = key.replace('video_', '').replace('_', ' ').title()
                print(f"  {CYAN}{nice_key}{RESET}  : {vid[key]}")

    if 'timezone_analysis' in r:
        tz = r['timezone_analysis']
        print('')
        print(f"  {BOLD}{YELLOW}--- TIMEZONE ANALYSIS ---{RESET}")
        if 'upload_time_utc' in tz:
            print(f"  {YELLOW}Upload Time (UTC){RESET}  : {tz['upload_time_utc']}")
        if 'upload_time_local' in tz:
            print(f"  {YELLOW}Upload Time (Local){RESET}: {tz['upload_time_local']}")
        if 'timezone_offset' in tz:
            print(f"  {YELLOW}Timezone{RESET}           : UTC{tz['timezone_offset']}")
        if 'possible_regions' in tz:
            print(f"  {YELLOW}Possible Regions{RESET}   : {', '.join(tz['possible_regions'])}")
        if 'gps_time' in tz:
            print(f"  {YELLOW}GPS Time{RESET}           : {tz['gps_time']}")
        if 'gps_timezone' in tz:
            print(f"  {YELLOW}GPS Timezone{RESET}       : {tz['gps_timezone']}")

    print('')
    print(f"{CYAN}{'=' * 60}{RESET}")


def get_url_page_info(url):
    result = {}
    platform = get_platform(url)
    result['platform'] = platform
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        req.add_header('User-Agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        req.add_header('Accept-Language', 'en-US,en;q=0.9')
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
        titles = re.findall(r'<title[^>]*>([^<]+)</title>', html)
        if titles:
            result['page_title'] = titles[0].strip()
        if platform == 'google_drive':
            file_id_match = re.search(r'([-a-zA-Z0-9_]{20,})', html)
            if file_id_match:
                result['file_id'] = file_id_match.group(1)
            file_name_match = re.findall(r'"fileName":\s*"([^"]+)"', html)
            if file_name_match:
                result['file_name'] = file_name_match.group(1)
            file_size_match = re.findall(r'"sizeBytes":\s*"?(\d+)"?', html)
            if file_size_match:
                size_bytes = int(file_size_match.group(1))
                if size_bytes > 1024*1024:
                    result['file_size'] = f"{size_bytes/1024/1024:.1f} MB"
                elif size_bytes > 1024:
                    result['file_size'] = f"{size_bytes/1024:.1f} KB"
                else:
                    result['file_size'] = f"{size_bytes} bytes"
            mime_match = re.findall(r'"mimeType":\s*"([^"]+)"', html)
            if mime_match:
                result['mime_type'] = mime_match.group(1)
            created_match = re.findall(r'"createdTime":\s*"([^"]+)"', html)
            if created_match:
                result['created'] = created_match.group(1)
            modified_match = re.findall(r'"modifiedTime":\s*"([^"]+)"', html)
            if modified_match:
                result['modified'] = modified_match.group(1)
        og_tags = re.findall(r'<meta[^>]*property="og:([^"]*)"[^>]*content="([^"]*)"', html)
        for key, val in og_tags:
            if key == 'title':
                result['og_title'] = val
            elif key == 'description':
                result['og_description'] = val
            elif key == 'image':
                result['og_image'] = val
        twitter_tags = re.findall(r'<meta[^>]*name="twitter:([^"]*)"[^>]*content="([^"]*)"', html)
        for key, val in twitter_tags:
            if key == 'title':
                result['twitter_title'] = val
            elif key == 'description':
                result['twitter_description'] = val
        dates = re.findall(r'datetime="([^"]*)"', html)
        if dates:
            result['post_date'] = dates[0]
        authors = re.findall(r'"author":\s*\{[^}]*"name":\s*"([^"]*)"', html)
        if authors:
            result['author'] = authors[0]
        keywords = re.findall(r'<meta[^>]*name="keywords"[^>]*content="([^"]*)"', html)
        if keywords:
            result['keywords'] = keywords[0]
        result['url'] = url
        result['status'] = 'accessible'
    except Exception as e:
        result['status'] = str(e)
        result['url'] = url
    return result


def main():
    if len(sys.argv) < 2:
        print('')
        print(f"  {BOLD}{CYAN}Usage:{RESET} tracer.py <file_or_url>")
        print('')
        print(f"  {GREEN}Commands:{RESET}")
        print(f"    {DIM}tracer.py photo.jpg{RESET}")
        print(f"    {DIM}tracer.py https://instagram.com/p/ABC123/{RESET}")
        print(f"    {DIM}tracer.py https://twitter.com/user/status/123{RESET}")
        print(f"    {DIM}tracer.py https://facebook.com/photo.php?fbid=123{RESET}")
        print(f"    {DIM}tracer.py /path/to/photos/{RESET}")
        print('')
        print(f"  {DIM}Part of OwlsHook Forensic Toolkit{RESET}")
        print('')
        sys.exit(1)

    target = sys.argv[1]
    is_url = target.startswith('http://') or target.startswith('https://')

    if is_url:
        print(f'\n  {GREEN}Downloading:{RESET} {target}')
        page_info = get_url_page_info(target)
        fpath = download(target)
        if not fpath:
            print(f'  {RED}Failed to download image!{RESET}')
            if 'google_drive' in get_platform(target):
                print(f'\n  {YELLOW}Google Drive Tips:{RESET}')
                print(f'  {DIM}1. Make sure file is shared publicly{RESET}')
                print(f'  {DIM}2. Click "Share" → "Anyone with link"{RESET}')
                print(f'  {DIM}3. Download file manually, then analyze:{RESET}')
                print(f'  {DIM}   owlshook trace downloaded_photo.jpg{RESET}')
            print(f'\n  {BOLD}{WHITE}--- URL INFO ---{RESET}')
            for k, v in page_info.items():
                print(f"  {GREEN}{k:14}{RESET}: {v}")
            sys.exit(0)
        print(f'  {GREEN}Saved to:{RESET} {fpath}')
        r = analyze(fpath, url=target)
        for k, v in page_info.items():
            if k not in r:
                r[k] = v
        show(r)
        cleanup(fpath)

    elif os.path.isfile(target):
        r = analyze(target)
        show(r)

    elif os.path.isdir(target):
        print(f'\n  Scanning: {target}\n')
        count = 0
        for root, dirs, files in os.walk(target):
            for name in files:
                fpath = os.path.join(root, name)
                r = analyze(fpath)
                show(r)
                count += 1
        print(f'\n  Total files scanned: {count}')

    else:
        print('  File not found!')
        sys.exit(1)


if __name__ == '__main__':
    main()
