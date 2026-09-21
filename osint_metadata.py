#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import re
import hashlib
import struct
import tempfile
import urllib.request
import ssl
from urllib.parse import urlparse
from datetime import datetime

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

BANNER = r"""
  ______          ___       _____ _    _  ____   ____  _  __
 / __ \ \        / / |     / ____| |  | |/ __ \ / __ \| |/ /
| |  | \ \  /\  / /| |    | (___ | |__| | |  | | |  | | ' / 
| |  | |\ \/  \/ / | |     \___ \|  __  | |  | | |  | |  <  
| |__| | \  /\  /  | |____ ____) | |  | | |__| | |__| | . \ 
 \____/   \/  \/   |______|_____/|_|  |_|\____/ \____/|_|\_\
"""

def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def extract_all_metadata(filepath):
    metadata = {}
    exiftool_json = run_cmd(f'exiftool -json -a -u -g1 "{filepath}"')
    if exiftool_json:
        try:
            data = json.loads(exiftool_json)
            if data:
                metadata['exiftool'] = data[0]
        except:
            pass
    iptc = run_cmd(f'exiftool -IPTC:all "{filepath}"')
    if iptc:
        metadata['iptc'] = {}
        for line in iptc.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                metadata['iptc'][key.strip()] = val.strip()
    xmp = run_cmd(f'exiftool -XMP:all "{filepath}"')
    if xmp:
        metadata['xmp'] = {}
        for line in xmp.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                metadata['xmp'][key.strip()] = val.strip()
    icc = run_cmd(f'exiftool -ICC_Profile:all "{filepath}"')
    if icc:
        metadata['icc_profile'] = icc[:500]
    return metadata

def extract_gps_from_all_sources(metadata):
    gps_data = {}
    if 'exiftool' in metadata:
        exif = metadata['exiftool']
        gps_keys = {k: v for k, v in exif.items() if 'GPS' in k or 'gps' in k}
        if gps_keys:
            gps_data['gps_tags'] = gps_keys
    if 'xmp' in metadata:
        xmp = metadata['xmp']
        for key, val in xmp.items():
            if 'gps' in key.lower() or 'location' in key.lower() or 'latitude' in key.lower() or 'longitude' in key.lower():
                gps_data[key] = val
    return gps_data

def extract_camera_fingerprint(metadata):
    fingerprint = {}
    if 'exiftool' in metadata:
        exif = metadata['exiftool']
        camera_fields = ['Make', 'Model', 'Software', 'LensModel', 'LensMake',
                        'FocalLength', 'FNumber', 'ISO', 'ExposureTime',
                        'Flash', 'WhiteBalance', 'ColorSpace']
        for field in camera_fields:
            for key, val in exif.items():
                if field.lower() in key.lower():
                    fingerprint[key] = val
    return fingerprint

def extract_timestamps(metadata):
    timestamps = {}
    time_fields = ['DateTimeOriginal', 'CreateDate', 'ModifyDate',
                   'GPSDateStamp', 'GPSTimeStamp', 'SubSecTimeOriginal',
                   'SubSecTimeDigitized', 'OffsetTimeOriginal',
                   'OffsetTimeDigitized']
    if 'exiftool' in metadata:
        exif = metadata['exiftool']
        for field in time_fields:
            for key, val in exif.items():
                if field.lower() in key.lower():
                    timestamps[key] = val
    return timestamps

def extract_software_info(metadata):
    software = {}
    if 'exiftool' in metadata:
        exif = metadata['exiftool']
        sw_fields = ['Software', 'ProcessingSoftware', 'HostComputer',
                    'CreatorTool', 'HistoryAction', 'HistoryInstanceID']
        for field in sw_fields:
            for key, val in exif.items():
                if field.lower() in key.lower():
                    software[key] = val
    return software

def extract_ai_indicators(metadata, filepath):
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
        'meta ai', 'adobe firefly', 'canva ai', 'photoshop ai',
        'comfyui', 'automatic1111', 'webui', 'invokeai', 'diffus'
    ]
    if 'exiftool' in metadata:
        exif = metadata['exiftool']
        for key, val in exif.items():
            val_str = str(val).lower()
            for kw in ai_keywords:
                if kw in val_str:
                    indicators['ai_generated'] = True
                    indicators['signs'].append(f"EXIF: '{kw}' in {key}")
    try:
        p = subprocess.run(['strings', filepath], capture_output=True, text=True, timeout=10)
        if p.returncode == 0:
            strings_out = p.stdout.lower()
            for kw in ai_keywords:
                if kw in strings_out:
                    indicators['signs'].append(f"Strings: '{kw}' found")
                    indicators['ai_generated'] = True
    except:
        pass
    if 'exiftool' in metadata:
        exif = metadata['exiftool']
        make = str(exif.get('Make', '')).lower()
        model = str(exif.get('Model', '')).lower()
        software = str(exif.get('Software', '')).lower()
        if any(cam in make for cam in ['canon', 'nikon', 'sony', 'fuji', 'apple', 'samsung', 'google']):
            indicators['signs'].append("Real camera manufacturer detected")
        if 'adobe' in software:
            indicators['signs'].append("Adobe software detected")
    if indicators['ai_generated']:
        indicators['confidence'] = 'high' if len(indicators['signs']) >= 2 else 'medium'
    return indicators

def analyze_video_metadata(filepath):
    result = {}
    ext = os.path.splitext(filepath)[1].lower()
    video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv',
                  '.m4v', '.3gp', '.ts', '.mts', '.vob', '.m4a', '.mp3']
    if ext not in video_exts:
        return None
    ffprobe_data = run_cmd(f'ffprobe -v quiet -print_format json -show_format -show_streams "{filepath}"')
    if ffprobe_data:
        try:
            data = json.loads(ffprobe_data)
            if 'format' in data:
                fmt = data['format']
                result['duration'] = fmt.get('duration', 'N/A')
                result['size'] = fmt.get('size', 'N/A')
                result['bitrate'] = fmt.get('bit_rate', 'N/A')
                result['format_name'] = fmt.get('format_name', 'N/A')
                if 'tags' in fmt:
                    for key, val in fmt['tags'].items():
                        result[f'video_{key}'] = val
            if 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'video':
                        result['video_codec'] = stream.get('codec_name', 'N/A')
                        result['resolution'] = f"{stream.get('width', '?')}x{stream.get('height', '?')}"
                        result['fps'] = stream.get('r_frame_rate', 'N/A')
                    elif stream.get('codec_type') == 'audio':
                        result['audio_codec'] = stream.get('codec_name', 'N/A')
                        result['sample_rate'] = stream.get('sample_rate', 'N/A')
        except:
            pass
    return result if result else None

def analyze_file_hashes(filepath):
    hashes = {}
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        hashes['md5'] = hashlib.md5(data).hexdigest()
        hashes['sha1'] = hashlib.sha1(data).hexdigest()
        hashes['sha256'] = hashlib.sha256(data).hexdigest()
        hashes['ssdeep'] = run_cmd(f'ssdeep "{filepath}"')
    except:
        pass
    return hashes

def detect_steganography(filepath):
    indicators = []
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        if data[:3] == b'\xff\xd8\xff':
            if b'Photoshop' in data or b'8BIM' in data:
                indicators.append("Photoshop data detected")
            if b'ICC_PROFILE' in data:
                indicators.append("ICC Profile embedded")
            if b'XMP' in data:
                indicators.append("XMP data present")
            segments = []
            pos = 2
            while pos < len(data) - 1:
                if data[pos] == 0xFF:
                    marker = data[pos+1]
                    if marker in [0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
                                  0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCF]:
                        break
                    if marker == 0xDA:
                        break
                    if marker not in [0xD8, 0xD9, 0x00]:
                        try:
                            seg_len = struct.unpack('>H', data[pos+2:pos+4])[0]
                            segments.append((marker, seg_len))
                            pos += 2 + seg_len
                        except:
                            break
                    else:
                        pos += 2
                else:
                    pos += 1
            if len(segments) > 10:
                indicators.append(f"Multiple JPEG segments ({len(segments)})")
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            if b'iTXt' in data or b'tEXt' in data or b'zTXt' in data:
                indicators.append("Text chunks in PNG")
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            indicators.append("WebP format detected")
    except:
        pass
    return indicators

def full_forensic_analysis(filepath, url=None):
    result = {
        'file_path': filepath,
        'file_name': os.path.basename(filepath),
        'file_size': os.path.getsize(filepath),
        'file_type': run_cmd(f'file -b "{filepath}"')
    }
    hashes = analyze_file_hashes(filepath)
    result['hashes'] = hashes
    all_metadata = extract_all_metadata(filepath)
    result['metadata'] = all_metadata
    gps = extract_gps_from_all_sources(all_metadata)
    if gps:
        result['gps_data'] = gps
    camera = extract_camera_fingerprint(all_metadata)
    if camera:
        result['camera_fingerprint'] = camera
    timestamps = extract_timestamps(all_metadata)
    if timestamps:
        result['timestamps'] = timestamps
    software = extract_software_info(all_metadata)
    if software:
        result['software_info'] = software
    ai = extract_ai_indicators(all_metadata, filepath)
    result['ai_analysis'] = ai
    video = analyze_video_metadata(filepath)
    if video:
        result['video_metadata'] = video
    steg = detect_steganography(filepath)
    if steg:
        result['steganography'] = steg
    return result

def print_report(result):
    print('')
    print(f"{CYAN}{'=' * 70}{RESET}")
    print(f"{BOLD}{WHITE}  OWLSHOOK FORENSIC REPORT{RESET}")
    print(f"{CYAN}{'=' * 70}{RESET}")
    print(f"  {GREEN}File{RESET}      : {result.get('file_name', 'Unknown')}")
    print(f"  {GREEN}Path{RESET}      : {result.get('file_path', 'N/A')}")
    print(f"  {GREEN}Size{RESET}      : {result.get('file_size', 0)} bytes")
    print(f"  {GREEN}Type{RESET}      : {result.get('file_type', 'N/A')}")
    if 'hashes' in result:
        h = result['hashes']
        print(f"  {GREEN}MD5{RESET}       : {h.get('md5', 'N/A')}")
        print(f"  {GREEN}SHA-1{RESET}     : {h.get('sha1', 'N/A')}")
        print(f"  {GREEN}SHA-256{RESET}   : {h.get('sha256', 'N/A')}")
    if 'gps_data' in result:
        gps = result['gps_data']
        print('')
        print(f"  {BOLD}{GREEN}✅ GPS DATA FOUND{RESET}")
        print(f"  {GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for key, val in gps.items():
            if key != 'gps_tags':
                print(f"  {YELLOW}{key}{RESET}     : {val}")
        if 'gps_tags' in gps:
            for key, val in gps['gps_tags'].items():
                print(f"  {YELLOW}{key}{RESET} : {val}")
    elif 'camera_fingerprint' in result:
        cam = result['camera_fingerprint']
        print('')
        print(f"  {BOLD}{YELLOW}📷 CAMERA FINGERPRINT (No GPS){RESET}")
        print(f"  {YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for key, val in cam.items():
            print(f"  {YELLOW}{key}{RESET} : {val}")
    if 'timestamps' in result:
        ts = result['timestamps']
        print('')
        print(f"  {BOLD}{CYAN}⏰ TIMESTAMPS{RESET}")
        print(f"  {CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for key, val in ts.items():
            print(f"  {CYAN}{key}{RESET} : {val}")
    if 'software_info' in result:
        sw = result['software_info']
        print('')
        print(f"  {BOLD}{MAGENTA}💻 SOFTWARE INFO{RESET}")
        print(f"  {MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for key, val in sw.items():
            print(f"  {MAGENTA}{key}{RESET} : {val}")
    if 'ai_analysis' in result:
        ai = result['ai_analysis']
        print('')
        print(f"  {BOLD}{MAGENTA}🤖 AI ANALYSIS{RESET}")
        print(f"  {MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        if ai.get('ai_generated'):
            print(f"  {RED}⚠ AI GENERATED: YES (Confidence: {ai.get('confidence', 'N/A').upper()}){RESET}")
        else:
            print(f"  {GREEN}✓ AI GENERATED: NO (Likely real content){RESET}")
        if ai.get('signs'):
            for sign in ai['signs']:
                print(f"    {DIM}• {sign}{RESET}")
    if 'video_metadata' in result:
        vid = result['video_metadata']
        print('')
        print(f"  {BOLD}{CYAN}🎬 VIDEO METADATA{RESET}")
        print(f"  {CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        for key, val in vid.items():
            print(f"  {CYAN}{key}{RESET} : {val}")
    if 'steganography' in result:
        steg = result['steganography']
        if steg:
            print('')
            print(f"  {BOLD}{YELLOW}🔍 STEGANOGRAPHY INDICATORS{RESET}")
            print(f"  {YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
            for indicator in steg:
                print(f"  {YELLOW}• {indicator}{RESET}")
    if 'metadata' in result and 'exiftool' in result['metadata']:
        exif = result['metadata']['exiftool']
        print('')
        print(f"  {BOLD}{WHITE}--- FULL EXIF DATA ---{RESET}")
        print(f"  {DIM}(Showing non-empty fields){RESET}")
        for key, val in exif.items():
            if val and str(val).strip() and key not in ['SourceFile', 'ExifToolVersion']:
                print(f"  {GREEN}{key:30}{RESET}: {val}")
    print('')
    print(f"{CYAN}{'=' * 70}{RESET}")

def download_file(url):
    try:
        from urllib.parse import quote, urlunparse
        tmp = tempfile.mkdtemp()
        parsed = urlparse(url)
        encoded_path = quote(parsed.path)
        clean_url = urlunparse(parsed._replace(path=encoded_path))
        name = os.path.basename(parsed.path).split('?')[0]
        if '.' not in name:
            name = 'download.jpg'
        name = re.sub(r'[^\w\-.]', '_', name)
        fpath = os.path.join(tmp, name)
        referer = f'{parsed.scheme}://{parsed.netloc}/'

        file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if not file_id_match:
            file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if file_id_match and 'drive.google.com' in url:
            file_id = file_id_match.group(1)
            download_url = f'https://drive.google.com/uc?export=download&id={file_id}&confirm=t'
            result = subprocess.run([
                'curl', '-sk', '-L', '-o', fpath,
                '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-H', 'Referer: https://drive.google.com/',
                '--max-time', '30',
                download_url
            ], capture_output=True, text=True, timeout=35)
            if os.path.exists(fpath) and os.path.getsize(fpath) > 100:
                with open(fpath, 'rb') as f:
                    header = f.read(200)
                if b'<!DOCTYPE' in header or b'<html' in header:
                    os.remove(fpath)
                    return None
                return fpath
            return None
        else:
            result = subprocess.run([
                'curl', '-sk', '-L', '-o', fpath,
                '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-H', 'Accept: image/webp,image/apng,image/*,*/*;q=0.8',
                '-H', f'Referer: {referer}',
                '--max-time', '30',
                clean_url
            ], capture_output=True, text=True, timeout=35)
            if os.path.exists(fpath) and os.path.getsize(fpath) > 100:
                return fpath

        if os.path.exists(fpath):
            os.remove(fpath)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(clean_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        req.add_header('Accept', 'image/*,*/*;q=0.8')
        req.add_header('Referer', referer)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            with open(fpath, 'wb') as f:
                f.write(r.read())
        if os.path.getsize(fpath) < 100:
            return None
        return fpath
    except:
        return None


def main():
    if len(sys.argv) < 2:
        print(f"{CYAN}{BANNER}{RESET}")
        print(f"  {BOLD}Advanced OSINT & Forensic Metadata Extractor{RESET}")
        print()
        print(f"  {GREEN}Usage:{RESET} owlshook osint <file_or_url>")
        print()
        print(f"  {GREEN}Examples:{RESET}")
        print(f"    {DIM}owlshook osint photo.jpg{RESET}")
        print(f"    {DIM}owlshook osint video.mp4{RESET}")
        print(f"    {DIM}owlshook osint https://instagram.com/p/ABC123/{RESET}")
        print(f"    {DIM}owlshook osint https://twitter.com/user/status/123{RESET}")
        print()
        print(f"  {GREEN}Extracts:{RESET}")
        print(f"    {DIM}• GPS coordinates (all sources){RESET}")
        print(f"    {DIM}• Camera fingerprint{RESET}")
        print(f"    {DIM}• Software/editor info{RESET}")
        print(f"    {DIM}• AI generation detection{RESET}")
        print(f"    {DIM}• Video metadata{RESET}")
        print(f"    {DIM}• File hashes (MD5/SHA1/SHA256){RESET}")
        print(f"    {DIM}• Steganography indicators{RESET}")
        print(f"    {DIM}• Timestamps{RESET}")
        print(f"    {DIM}• Full EXIF dump{RESET}")
        print()
        sys.exit(1)

    target = sys.argv[1]
    is_url = target.startswith('http://') or target.startswith('https://')

    if is_url:
        print(f'\n  {GREEN}Downloading:{RESET} {target}')
        fpath = download_file(target)
        if not fpath:
            print(f'  {RED}Failed to download! Try downloading manually and analyze the local file.{RESET}')
            sys.exit(1)
        print(f'  {GREEN}Saved to:{RESET} {fpath}')
        print(f"\n  {GREEN}Analyzing:{RESET} {target}")
        print(f"  {DIM}Please wait...{RESET}\n")
        result = full_forensic_analysis(fpath)
        result['source_url'] = target
        print_report(result)
        try:
            os.remove(fpath)
            os.rmdir(os.path.dirname(fpath))
        except:
            pass
    elif os.path.exists(target):
        print(f"\n  {GREEN}Analyzing:{RESET} {target}")
        print(f"  {DIM}Please wait...{RESET}\n")
        result = full_forensic_analysis(target)
        print_report(result)
    else:
        print(f"{RED}[!] File not found: {target}{RESET}")
        sys.exit(1)

if __name__ == '__main__':
    main()
