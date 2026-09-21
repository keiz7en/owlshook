#!/usr/bin/env python3

import os
import sys
import json
import hashlib
import struct
import subprocess
import datetime
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote

try:
    import urllib.request
    import urllib.error
    import ssl
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

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
    b'RIFF': ('RIFF Container', '.wav'),
    b'ID3': ('MP3 Audio', '.mp3'),
    b'\xff\xfb': ('MP3 Audio', '.mp3'),
    b'\xff\xf3': ('MP3 Audio', '.mp3'),
    b'\xff\xf2': ('MP3 Audio', '.mp3'),
    b'OggS': ('OGG Audio', '.ogg'),
    b'fLaC': ('FLAC Audio', '.flac'),
    b'\x1a\x45\xdf\xa3': ('MKV Video', '.mkv'),
}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
]

SOCIAL_PATTERNS = {
    'instagram': {
        'patterns': [
            r'instagram\.com/p/([A-Za-z0-9_-]+)',
            r'instagram\.com/reel/([A-Za-z0-9_-]+)',
            r'instagram\.com/tv/([A-Za-z0-9_-]+)',
            r'cdninstagram\.com',
            r'instagram\.[a-z]+.*\.fbcdn\.net',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
            r'(https?://[^"\s]+\.webp)',
        ],
    },
    'facebook': {
        'patterns': [
            r'facebook\.com/.+/photos/',
            r'facebook\.com/photo\.php',
            r'fbcdn\.net',
            r'facebook\.com.*\.jpg',
            r'facebook\.com.*\.png',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
            r'(https?://[^"\s]+\.webp)',
        ],
    },
    'twitter': {
        'patterns': [
            r'twitter\.com/.+/status/',
            r'x\.com/.+/status/',
            r'pbs\.twimg\.com',
            r'pic\.twitter\.com',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
            r'(https?://[^"\s]+\.webp)',
        ],
    },
    'tiktok': {
        'patterns': [
            r'tiktok\.com/.+/video/',
            r'vm\.tiktok\.com',
            r'tiktokcdn\.com',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.mp4)',
        ],
    },
    'youtube': {
        'patterns': [
            r'youtube\.com/watch',
            r'youtu\.be/',
            r'youtube\.com/shorts/',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.png)',
        ],
    },
    'reddit': {
        'patterns': [
            r'reddit\.com/r/.+/comments/',
            r'preview\.redd\.it',
            r'i\.redd\.it',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
            r'(https?://[^"\s]+\.gif)',
        ],
    },
    'imgur': {
        'patterns': [
            r'imgur\.com/',
            r'i\.imgur\.com',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
            r'(https?://[^"\s]+\.gif)',
        ],
    },
    'linkedin': {
        'patterns': [
            r'linkedin\.com/posts/',
            r'linkedin\.com/feed/update/',
            r'media\.licdn\.com',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
        ],
    },
    'snapchat': {
        'patterns': [
            r'snapchat\.com/',
            r'sc-cdn\.net',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
        ],
    },
    'telegram': {
        'patterns': [
            r't\.me/',
            r'telegram\.org',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
        ],
    },
    'whatsapp': {
        'patterns': [
            r'whatsapp\.com',
            r'whatsapp:',
        ],
        'direct_patterns': [
            r'(https?://[^"\s]+\.jpg)',
            r'(https?://[^"\s]+\.jpeg)',
            r'(https?://[^"\s]+\.png)',
        ],
    },
}

IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.raw']
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg']


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
    url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
    for s in strings:
        found = url_pattern.findall(s)
        urls.extend(found)
    return list(set(urls))


def find_emails(strings):
    emails = []
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    for s in strings:
        found = email_pattern.findall(s)
        emails.extend(found)
    return list(set(emails))


def find_ip_addresses(strings):
    ips = []
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    for s in strings:
        found = ip_pattern.findall(s)
        for ip in found:
            parts = ip.split('.')
            if all(0 <= int(p) <= 255 for p in parts):
                ips.append(ip)
    return list(set(ips))


def identify_platform(url):
    url_lower = url.lower()
    for platform, config in SOCIAL_PATTERNS.items():
        for pattern in config['patterns']:
            if re.search(pattern, url_lower):
                return platform
    return 'unknown'


def extract_social_media_id(url):
    url_lower = url.lower()

    instagram_match = re.search(r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url_lower)
    if instagram_match:
        return {'platform': 'instagram', 'post_id': instagram_match.group(1)}

    facebook_match = re.search(r'facebook\.com/.+/photos/(\d+)', url_lower)
    if facebook_match:
        return {'platform': 'facebook', 'photo_id': facebook_match.group(1)}

    twitter_match = re.search(r'(?:twitter\.com|x\.com)/.+/status/(\d+)', url_lower)
    if twitter_match:
        return {'platform': 'twitter', 'tweet_id': twitter_match.group(1)}

    reddit_match = re.search(r'reddit\.com/r/.+/comments/([a-z0-9]+)', url_lower)
    if reddit_match:
        return {'platform': 'reddit', 'post_id': reddit_match.group(1)}

    tiktok_match = re.search(r'tiktok\.com/.+/video/(\d+)', url_lower)
    if tiktok_match:
        return {'platform': 'tiktok', 'video_id': tiktok_match.group(1)}

    return None


def download_file(url, timeout=30):
    import subprocess
    temp_dir = tempfile.mkdtemp(prefix='inspector_')
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path).split('?')[0]
    if not filename or '.' not in filename:
        filename = 'downloaded.jpg'
    filepath = os.path.join(temp_dir, filename)

    try:
        result = subprocess.run([
            'curl', '-sk', '-L',
            '-o', filepath,
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '-H', 'Accept: image/webp,image/apng,image/*,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', f'Referer: {parsed.scheme}://{parsed.netloc}/',
            '--max-time', '30',
            url
        ], capture_output=True, text=True, timeout=35)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            return filepath, None
    except Exception:
        pass

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url)
        req.add_header('User-Agent', USER_AGENTS[0])
        req.add_header('Accept', 'image/webp,image/apng,image/*,*/*;q=0.8')
        req.add_header('Referer', f'{parsed.scheme}://{parsed.netloc}/')
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            with open(filepath, 'wb') as f:
                f.write(response.read())
        if os.path.getsize(filepath) > 100:
            return filepath, None
    except Exception as e:
        return None, str(e)

    return None, "Download failed"


def download_from_instagram(url):
    try:
        import re as re2
        post_id_match = re2.search(r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)', url)
        if post_id_match:
            post_id = post_id_match.group(1)
            api_url = f'https://www.instagram.com/p/{post_id}/?__a=1&__d=dis'
            filepath, error = download_file(api_url)
            if not error:
                return filepath, None
    except Exception:
        pass
    return download_file(url)


def download_from_facebook(url):
    return download_file(url)


def download_from_twitter(url):
    try:
        import re as re2
        tweet_match = re2.search(r'(?:twitter\.com|x\.com)/.+/status/(\d+)', url)
        if tweet_match:
            tweet_id = tweet_match.group(1)
            embed_url = f'https://publish.twitter.com/oembed?url=https://twitter.com/i/status/{tweet_id}'
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(embed_url)
            req.add_header('User-Agent', USER_AGENTS[0])
            with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                data = json.loads(response.read())
                html = data.get('html', '')
                img_matches = re2.findall(r'(https?://pbs\.twimg\.com/media/[^\s"]+)', html)
                if img_matches:
                    img_url = img_matches[0].replace('&amp;', '&')
                    if '?' not in img_url:
                        img_url += '?format=jpg&name=large'
                    return download_file(img_url)
    except Exception:
        pass
    return download_file(url)


def download_from_reddit(url):
    try:
        import re as re2
        api_url = url.rstrip('/') + '.json'
        filepath, error = download_file(api_url)
        if not error:
            with open(filepath, 'r') as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                post_data = data[0].get('data', {}).get('children', [{}])[0].get('data', {})
                image_url = post_data.get('url')
                if image_url and any(ext in image_url.lower() for ext in IMAGE_EXTENSIONS):
                    os.remove(filepath)
                    return download_file(image_url)
            os.remove(filepath)
    except Exception:
        pass
    return download_file(url)


def download_from_imgur(url):
    try:
        import re as re2
        imgur_match = re2.search(r'imgur\.com/([a-zA-Z0-9]+)', url)
        if imgur_match:
            img_id = imgur_match.group(1)
            direct_url = f'https://i.imgur.com/{img_id}.jpg'
            filepath, error = download_file(direct_url)
            if not error:
                return filepath, None
    except Exception:
        pass
    return download_file(url)


def download_from_youtube(url):
    try:
        import re as re2
        video_id_match = re2.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]+)', url)
        if video_id_match:
            video_id = video_id_match.group(1)
            thumbnail_url = f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            filepath, error = download_file(thumbnail_url)
            if not error:
                with open(filepath, 'rb') as f:
                    header = f.read(4)
                if header == b'\xff\xd8\xff\xe0' or header == b'\xff\xd8\xff\xe1':
                    return filepath, None
                thumbnail_url = f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
                os.remove(filepath)
                return download_file(thumbnail_url)
    except Exception:
        pass
    return download_file(url)


def download_from_linkedin(url):
    return download_file(url)


def download_from_generic(url):
    return download_file(url)


def download_media(url, platform=None):
    if platform is None:
        platform = identify_platform(url)

    downloaders = {
        'instagram': download_from_instagram,
        'facebook': download_from_facebook,
        'twitter': download_from_twitter,
        'reddit': download_from_reddit,
        'imgur': download_from_imgur,
        'youtube': download_from_youtube,
        'linkedin': download_from_linkedin,
    }

    downloader = downloaders.get(platform, download_from_generic)
    return downloader(url)


def analyze_file(filepath, source_url=None):
    if not os.path.exists(filepath):
        return {'error': 'File not found'}

    result = {
        'file': filepath,
        'filename': os.path.basename(filepath),
        'filesize': os.path.getsize(filepath),
        'filesize_human': f"{os.path.getsize(filepath) / 1024:.2f} KB" if os.path.getsize(filepath) < 1024*1024 else f"{os.path.getsize(filepath) / (1024*1024):.2f} MB",
    }

    if source_url:
        result['source_url'] = source_url
        result['platform'] = identify_platform(source_url)
        social_id = extract_social_media_id(source_url)
        if social_id:
            result['social_media'] = social_id

    file_type = detect_file_type(filepath)
    result['file_type'] = file_type['type']
    result['detected_extension'] = file_type['extension']

    result['timestamps'] = get_file_timestamps(filepath)
    result['hashes'] = get_file_hashes(filepath)

    strings = extract_embedded_strings(filepath)
    if strings:
        result['embedded_strings'] = {
            'total_count': len(strings),
            'urls': find_urls(strings),
            'emails': find_emails(strings),
            'ip_addresses': find_ip_addresses(strings),
        }

    ext = Path(filepath).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        exif = get_exif_data(filepath)
        if exif:
            result['exif'] = exif
            gps_data = {}
            for key, val in exif.items():
                if 'gps' in key.lower():
                    gps_data[key] = val
            if gps_data:
                result['gps'] = gps_data
                lat = None
                lon = None
                for key, val in gps_data.items():
                    if 'latitude' in key.lower() and 'ref' not in key.lower():
                        try:
                            if isinstance(val, str):
                                lat = float(val)
                            elif isinstance(val, list) and len(val) >= 3:
                                lat = val[0] + val[1]/60 + val[2]/3600
                        except:
                            pass
                    if 'longitude' in key.lower() and 'ref' not in key.lower():
                        try:
                            if isinstance(val, str):
                                lon = float(val)
                            elif isinstance(val, list) and len(val) >= 3:
                                lon = val[0] + val[1]/60 + val[2]/3600
                        except:
                            pass
                if lat and lon:
                    result['google_maps'] = f'https://www.google.com/maps?q={lat},{lon}'

    elif ext == '.pdf':
        try:
            proc = subprocess.run(
                ['exiftool', '-json', filepath],
                capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                if data:
                    result['pdf_metadata'] = data[0]
        except Exception:
            pass

    elif ext in ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'):
        try:
            proc = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath],
                capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                result['video_metadata'] = json.loads(proc.stdout)
        except Exception:
            pass

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


def analyze_url(url):
    print(f"[*] Platform: {identify_platform(url)}")
    social_id = extract_social_media_id(url)
    if social_id:
        print(f"[*] Social ID: {social_id}")

    print(f"[*] Downloading from: {url}")
    filepath, error = download_media(url)

    if error:
        return {'error': f'Download failed: {error}', 'url': url}

    print(f"[*] Downloaded to: {filepath}")

    result = analyze_file(filepath, source_url=url)

    try:
        os.remove(filepath)
        os.rmdir(os.path.dirname(filepath))
    except Exception:
        pass

    return result


def analyze_local(filepath):
    return analyze_file(filepath)


def print_result(result):
    print("=" * 70)
    print(f"FILE: {result.get('filename', 'Unknown')}")
    print("=" * 70)

    if 'source_url' in result:
        print(f"  Source URL      : {result['source_url']}")
        print(f"  Platform        : {result.get('platform', 'Unknown')}")

    if 'social_media' in result:
        sm = result['social_media']
        print(f"  Post ID         : {sm.get('post_id', sm.get('tweet_id', sm.get('photo_id', sm.get('video_id', ''))))}")

    print(f"  Path            : {result.get('file', '')}")
    print(f"  File Size       : {result.get('filesize_human', '')}")
    print(f"  File Type       : {result.get('file_type', '')}")

    if 'timestamps' in result:
        ts = result['timestamps']
        print(f"  Created         : {ts.get('created', 'N/A')}")
        print(f"  Modified        : {ts.get('modified', 'N/A')}")

    if 'hashes' in result:
        h = result['hashes']
        print(f"  MD5             : {h.get('md5', '')}")
        print(f"  SHA-256         : {h.get('sha256', '')}")

    if 'file_command' in result:
        print(f"  File Command    : {result.get('file_command', '')}")

    if 'gps' in result:
        print("\n  --- GPS LOCATION ---")
        gps = result['gps']
        for key, val in gps.items():
            print(f"  {key:18}: {val}")

    if 'google_maps' in result:
        print(f"\n  Google Maps     : {result['google_maps']}")

    if 'exif' in result:
        print("\n  --- EXIF DATA ---")
        for key, val in result['exif'].items():
            if 'thumbnail' not in key.lower() and 'sourcefile' not in key.lower():
                print(f"  {key:30}: {val}")

    if 'pdf_metadata' in result:
        print("\n  --- PDF METADATA ---")
        for key, val in result['pdf_metadata'].items():
            if 'sourcefile' not in key.lower():
                print(f"  {key:30}: {val}")

    if 'video_metadata' in result:
        print("\n  --- VIDEO METADATA ---")
        vm = result['video_metadata']
        if 'format' in vm:
            fmt = vm['format']
            print(f"  Duration        : {fmt.get('duration', 'N/A')} seconds")
            print(f"  Size            : {fmt.get('size', 'N/A')} bytes")
            print(f"  Bit Rate        : {fmt.get('bit_rate', 'N/A')}")
            print(f"  Format          : {fmt.get('format_long_name', fmt.get('format_name', 'N/A'))}")

    if 'embedded_strings' in result:
        es = result['embedded_strings']
        if es.get('urls'):
            print(f"\n  --- URLS FOUND ({len(es['urls'])}) ---")
            for url in es['urls'][:10]:
                print(f"  {url}")
        if es.get('emails'):
            print(f"\n  --- EMAILS FOUND ({len(es['emails'])}) ---")
            for email in es['emails'][:10]:
                print(f"  {email}")
        if es.get('ip_addresses'):
            print(f"\n  --- IP ADDRESSES FOUND ({len(es['ip_addresses'])}) ---")
            for ip in es['ip_addresses'][:10]:
                print(f"  {ip}")

    print()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_or_url> [output.json]")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} photo.jpg")
        print(f"  {sys.argv[0]} https://www.instagram.com/p/ABC123/")
        print(f"  {sys.argv[0]} https://twitter.com/user/status/123456")
        print(f"  {sys.argv[0]} https://www.facebook.com/photo.php?fbid=123")
        print(f"  {sys.argv[0]} https://i.imgur.com/abc.jpg")
        print(f"  {sys.argv[0]} https://www.youtube.com/watch?v=abc123")
        print(f"  {sys.argv[0]} /path/to/folder/")
        print(f"  {sys.argv[0]} photo.jpg output.json")
        sys.exit(1)

    target = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    is_url = target.startswith('http://') or target.startswith('https://')

    if is_url:
        result = analyze_url(target)
        print_result(result)
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Report saved to {output_file}")

    elif os.path.isfile(target):
        result = analyze_local(target)
        print_result(result)
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Report saved to {output_file}")

    elif os.path.isdir(target):
        print(f"Scanning directory: {target}")
        print()
        results = []
        for root, dirs, files in os.walk(target):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    data = analyze_local(filepath)
                    results.append(data)
                    print_result(data)
                except Exception:
                    pass
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Report saved to {output_file}")

    else:
        print("Invalid path or URL.")
        sys.exit(1)


if __name__ == '__main__':
    main()
