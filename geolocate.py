#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import re
import urllib.request
import urllib.error
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

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except:
        return ""

def check_exif_gps(filepath):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  METHOD 1: EXIF GPS METADATA{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    output = run_cmd(f'exiftool -GPSLatitude -GPSLongitude -GPSLatitudeRef -GPSLongitudeRef "{filepath}" 2>/dev/null')
    
    if output and "GPS" in output:
        print(f"\n  {GREEN}[+] GPS DATA FOUND IN EXIF!{RESET}")
        print(f"\n{output}")
        
        lat_match = re.search(r'GPS Latitude\s*:\s*([\d.\-]+)', output)
        lon_match = re.search(r'GPS Longitude\s*:\s*([\d.\-]+)', output)
        
        if lat_match and lon_match:
            lat = lat_match.group(1)
            lon = lon_match.group(1)
            print(f"\n  {GREEN}Coordinates:{RESET} {lat}, {lon}")
            print(f"  {GREEN}Google Maps:{RESET} https://maps.google.com/?q={lat},{lon}")
        return True
    else:
        print(f"\n  {YELLOW}[i] No GPS in EXIF (stripped by platform){RESET}")
        print(f"  {DIM}Try: Download original file before upload{RESET}")
        return False

def check_url_metadata(url):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  METHOD 6: URL/META DATA ANALYSIS{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        html = response.read().decode('utf-8', errors='ignore')
        
        geo_patterns = [
            (r'og:latitude["\s]*content="([^"]+)"', 'og:latitude'),
            (r'og:longitude["\s]*content="([^"]+)"', 'og:longitude'),
            (r'geo\.position["\s]*content="([^"]+)"', 'geo.position'),
            (r'"latitude"\s*:\s*([\d.\-]+)', 'JSON latitude'),
            (r'"longitude"\s*:\s*([\d.\-]+)', 'JSON longitude'),
            (r'"lat"\s*:\s*([\d.\-]+)', 'JSON lat'),
            (r'"lon"\s*:\s*([\d.\-]+)', 'JSON lon'),
            (r'"lng"\s*:\s*([\d.\-]+)', 'JSON lng'),
            (r'data-lat="([^"]+)"', 'data-lat'),
            (r'data-lng="([^"]+)"', 'data-lng'),
            (r'google\.com/maps\?.*?q=([\d.\-]+,[\d.\-]+)', 'Google Maps link'),
        ]
        
        found = False
        for pattern, name in geo_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                print(f"\n  {GREEN}[+] Found {name}: {match.group(1)}{RESET}")
                found = True
        
        if not found:
            print(f"\n  {YELLOW}[i] No location data in page metadata{RESET}")
            
        location_patterns = [
            (r'"location"\s*:\s*"([^"]+)"', 'Location field'),
            (r'"place"\s*:\s*"([^"]+)"', 'Place field'),
            (r'"city"\s*:\s*"([^"]+)"', 'City field'),
            (r'"country"\s*:\s*"([^"]+)"', 'Country field'),
        ]
        
        for pattern, name in location_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                print(f"  {GREEN}[+] {name}: {match.group(1)}{RESET}")
                found = True
        
        return found
        
    except Exception as e:
        print(f"\n  {RED}[!] Error fetching URL: {e}{RESET}")
        return False

def check_social_context(filepath):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  METHOD 5: SOCIAL MEDIA CONTEXT CLUES{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    output = run_cmd(f'exiftool -UserComment -ImageDescription -Artist -Copyright -Byline "{filepath}" 2>/dev/null')
    
    if output:
        print(f"\n  {GREEN}[+] Text found in image metadata:{RESET}")
        for line in output.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                print(f"  {DIM}{key.strip()}: {val.strip()}{RESET}")
    
    strings_output = run_cmd(f'strings "{filepath}" | grep -iE "http|www|\.com|\.org|location|place|city|country|geo|lat|lon" | head -20')
    
    if strings_output:
        print(f"\n  {GREEN}[+] URLs/text found in image:{RESET}")
        for line in strings_output.split('\n')[:10]:
            print(f"  {DIM}{line.strip()}{RESET}")

def analyze_image(filepath):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  OWLSHOOK - MULTI-METHOD GEOLOCATION{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"\n  File: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"\n  {RED}[!] File not found: {filepath}{RESET}")
        return
    
    gps_found = check_exif_gps(filepath)
    check_social_context(filepath)
    
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}  RECOMMENDED NEXT STEPS{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    if gps_found:
        print(f"\n  {GREEN}[✓] GPS found! Use Google Maps link above.{RESET}")
    else:
        print(f"\n  {YELLOW}No GPS found. Try these techniques:{RESET}")
        print(f"\n  1. {BOLD}Reverse Image Search{RESET}")
        print(f"     Upload to: images.google.com")
        print(f"     Upload to: tineye.com")
        print(f"     Upload to: yandex.com/images")
        print(f"     Find original source → download original → check EXIF")
        
        print(f"\n  2. {BOLD}Visual Analysis{RESET}")
        print(f"     Look for: street signs, landmarks, text")
        print(f"     Check: Google Street View for matching scenes")
        
        print(f"\n  3. {BOLD}Social Context{RESET}")
        print(f"     Check: caption, hashtags, profile bio")
        print(f"     Look at: user's other posts")
        
        print(f"\n  4. {BOLD}Platform-Specific Tips{RESET}")
        print(f"     Instagram: Try downloading from API")
        print(f"     Facebook: Check photo page for metadata")
        print(f"     Twitter: Use ?format=json in URL")
        
        print(f"\n  5. {BOLD}Advanced Tools{RESET}")
        print(f"     FotoForensics.com (image analysis)")
        print(f"     SunCalc.org (shadow analysis)")
        print(f"     Mapillary.com (street photos)")
    
    print()

def main():
    if len(sys.argv) < 2:
        print(f"{CYAN}{BANNER}{RESET}")
        print(f"  {BOLD}Multi-Method Geolocation Tool{RESET}")
        print()
        print(f"  {GREEN}Usage:{RESET} owlshook geolocate <image_or_url>")
        print()
        print(f"  {GREEN}Examples:{RESET}")
        print(f"    {DIM}owlshook geolocate photo.jpg{RESET}")
        print(f"    {DIM}owlshook geolocate 'https://example.com/photo.jpg'{RESET}")
        print()
        print(f"  {DIM}Part of OwlsHook Forensic Toolkit{RESET}")
        print()
        sys.exit(1)
    
    target = sys.argv[1]
    
    if target.startswith('http://') or target.startswith('https://'):
        print(f"\n  {GREEN}Analyzing URL:{RESET} {target}")
        check_url_metadata(target)
    else:
        analyze_image(target)

if __name__ == '__main__':
    main()
