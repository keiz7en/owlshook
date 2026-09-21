#!/usr/bin/env python3
"""
OwlsHook - OSINT Geolocation Techniques
How to find GPS/location from photos even when metadata is stripped
"""

TECHNIQUES = """
╔══════════════════════════════════════════════════════════════════════╗
║           OSINT GEOLOCATION TECHNIQUES GUIDE                       ║
║           Finding Location From Photos                              ║
╚══════════════════════════════════════════════════════════════════════╝

Social media strips GPS, but location can still be found through
multiple techniques. Here are ALL methods:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 1: EXIF METADATA (Direct GPS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  When it works:
  - Original photos from phone/camera (before upload)
  - Some platforms DON'T strip metadata
  - Screenshots of EXIF viewers

  Platforms that KEEP GPS:
  ✓ Flickr (original size download)
  ✓ SmugMug (original download)
  ✓ Personal websites/blogs
  ✓ Cloud storage (Google Drive, Dropbox shared links)
  ✓ Email attachments
  ✓ Direct file transfers

  Platforms that STRIP GPS:
  ✗ Instagram, Facebook, Twitter/X
  ✗ Reddit, Imgur, TikTok
  ✓ BUT - can sometimes get GPS from:
    - Original file before upload
    - Screenshot of phone's photo viewer
    - Cloud backup (iCloud, Google Photos)

  How to check:
  $ owlshook gps photo.jpg
  $ exiftool photo.jpg | grep -i gps

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 2: REVERSE IMAGE SEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Find the ORIGINAL source which may have GPS:

  Google Images:  images.google.com
  TinEye:         tineye.com
  Yandex:         yandex.com/images
  Bing:           bing.com/images
  PimEyes:        pimeyes.com (face search)

  Steps:
  1. Upload the image
  2. Find original source
  3. Download original (not compressed version)
  4. Check EXIF of original

  Why this works:
  - Social media compresses images
  - Original source may retain GPS
  - Can find photographer's website

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 3: VISUAL GEOLOCATION (OSINT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Analyze image content for location clues:

  A) TEXT/SIGNS:
     - Street signs, shop names, billboards
     - Language on signs (Arabic = Middle East, etc.)
     - Phone numbers (country codes)
     - Car license plates
     - Building addresses

  B) LANDMARKS:
     - Famous buildings/monuments
     - Mountains, rivers, coastlines
     - Unique architecture
     - Religious buildings (mosques, churches, temples)

  C) INFRASTRUCTURE:
     - Road markings (white/yellow lines vary by country)
     - Traffic light style
     - Street lamp design
     - Power line style
     - Manhole covers (often city-specific)

  D) ENVIRONMENT:
     - Vegetation type (tropical, desert, etc.)
     - Climate clues (snow, tropical plants)
     - Soil/rock color
     - Sun position (shadows)

  Tools for visual analysis:
  - Google Earth/Street View
  - Mapillary.com (street-level photos)
  - Wikimapia.org
  - Google Maps satellite view

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 4: SHADOW ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Shadow direction tells you:
  - Hemisphere (North/South)
  - Time of day
  - Approximate latitude

  Rules:
  - Northern hemisphere: shadows point North
  - Southern hemisphere: shadows point South
  - Morning: shadows point West
  - Afternoon: shadows point East

  Tools:
  - SunCalc.org (sun position calculator)
  - ShadowCalculator.eu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 5: SOCIAL MEDIA CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Extract location from post context:

  A) CAPTIONS:
     - Hashtags (#NYC, #Dubai, #London)
     - Location tags
     - Check-in tags
     - "Currently at..." posts

  B) PROFILE INFO:
     - Bio location
     - Website links
     - Other posts with location

  C) COMMENTS:
     - People tagging location
     - Local language comments

  D) OTHER POSTS:
     - Same user's other photos
     - Location history
     - Geotagged posts from same time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 6: URL/META DATA ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Check the URL and page metadata:

  A) IMAGE URL:
     Sometimes contains location:
     - /photos/40.7128/-74.0060/...
     - ?lat=40.7128&lon=-74.006

  B) WEBPAGE META TAGS:
     <meta property="og:latitude" content="40.7128">
     <meta property="og:longitude" content="-74.006">
     <meta name="geo.position" content="40.7128;-74.006">

  C) PAGE SOURCE:
     - Embedded JSON-LD with location
     - JavaScript variables with coordinates
     - Hidden form fields

  How to check:
  $ owlshook url 'https://example.com/photo.jpg'
  $ curl -s 'URL' | grep -i "lat\|lon\|geo\|location"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 7: CAMERA FINGERPRINTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Each camera has unique sensor noise pattern:

  - Sensor dust spots
  - Lens distortion pattern
  - Color noise characteristics
  - Dead pixel patterns

  Tools:
  - FotoForensics.com (ELA analysis)
  - Amped Authenticate
  - Image Forensics (imageforensics.org)

  Use case:
  - Match photo to specific camera
  - Prove photos are from same device

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 8: WEATHER/HISTORICAL DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Cross-reference with weather/history:

  A) WEATHER:
     - Check historical weather for area
     - Cloud cover, precipitation
     - Temperature (clothing clues)

  B) VEGETATION:
     - Season (leaves, flowers)
     - Growth patterns

  C) EVENTS:
     - Construction in background
     - Events, festivals
     - Historical buildings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 9: IMAGE FORENSICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Analyze image for manipulation:

  A) ERROR LEVEL ANALYSIS (ELA):
     - Shows compression differences
     - Reveals edited regions
     - Can find original source

  B) JPEG QUANTIZATION:
     - Detects multiple saves
     - Identifies source platform

  C) CLONE DETECTION:
     - Find copy-pasted regions
     - Detect manipulation

  Tools:
  - FotoForensics.com
  - Forensically (29a.ch/photo-forensics)
  - JPEGsnoop

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

METHOD 10: ADVANCED OSINT TECHNIQUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  A) FLIGHT DATA:
     - Airplane wing photos → check FlightRadar24
     - Match flight path with time

  B) STAR/ASTRONOMY:
     - Night sky photos → identify stars
     - Determine hemisphere and time

  C) TIDE/WATER:
     - Coastal photos → check tide tables
     - Water levels match specific times

  D) EXIF CHAIN:
     - Screenshot → may keep original EXIF
     - Download from cloud → may have GPS
     - Check multiple copies of same image

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRACTICAL WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Step 1: Check EXIF directly
  $ owlshook gps photo.jpg

  Step 2: Try reverse image search
  - Upload to Google Images, TinEye, Yandex
  - Find original source

  Step 3: Check source page metadata
  $ owlshook url 'SOURCE_URL'

  Step 4: Visual analysis
  - Look for text, signs, landmarks
  - Check Google Street View

  Step 5: Social context
  - Check caption, hashtags, profile
  - Look at other posts

  Step 6: Advanced analysis
  - Shadow analysis
  - Weather correlation
  - Image forensics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEST PRACTICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. ALWAYS save original file (not screenshot)
  2. Check MULTIPLE sources for GPS
  3. Cross-reference DIFFERENT techniques
  4. Document your findings
  5. Use multiple tools (owlshook + exiftool + online)
  6. Consider context (who posted, when, where)

  Remember:
  - No single technique is 100% reliable
  - Combine multiple methods for accuracy
  - GPS is just ONE data point
  - Visual analysis is often most powerful

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOOLS REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OwlsHook Commands:
  $ owlshook gps photo.jpg          # Extract GPS
  $ owlshook trace photo.jpg        # Full analysis
  $ owlshook url 'URL'              # Analyze URL
  $ owlshook scan photo.jpg         # Complete scan
  $ owlshook dir /path/             # Batch scan

  Online Tools:
  - exiftool.org (EXIF viewer)
  - photos.google.com (Google Photos)
  - maps.google.com (Street View)
  - sunshadowmap.com (shadow analysis)
  - fotoforensics.com (image forensics)
  - mapillary.com (street photos)

  OSINT Tools:
  - Maltego (link analysis)
  - SpiderFoot (OSINT automation)
  - Shodan (device search)
  - theHarvester (email/domain)

╚══════════════════════════════════════════════════════════════════════╝
"""

print(TECHNIQUES)
