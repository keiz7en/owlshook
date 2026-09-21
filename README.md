# OwlsHook 🦉

> **Professional OSINT & Digital Forensics Toolkit**

```
  ______          ___       _____ _    _  ____   ____  _  __
 / __ \ \        / / |     / ____| |  | |/ __ \ / __ \| |/ /
| |  | \ \  /\  / /| |    | (___ | |__| | |  | | |  | | ' / 
| |  | |\ \/  \/ / | |     \___ \|  __  | |  | | |  | |  <  
| |__| | \  /\  /  | |____ ____) | |  | | |__| | |__| | . \ 
 \____/   \/  \/   |______|_____/|_|  |_|\____/ \____/|_|\_\
```

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OSINT](https://img.shields.io/badge/OSINT-Forensics-red.svg)](https://github.com/keiz7en/owlshook)
[![cybersecurity](https://img.shields.io/badge/CyberSec-Tool-orange.svg)](https://github.com/keiz7en/owlshook)

---

## 🔥 Features

| Feature | Description |
|---------|-------------|
| 📍 **GPS Extraction** | Extract GPS coordinates with Google Maps links |
| 🌐 **Server Geolocation** | IP-based location when GPS unavailable |
| 🤖 **AI Detection** | Detect AI-generated images/videos |
| ⏰ **Timezone Analysis** | Predict location from upload time |
| 🎬 **Video Analysis** | Full metadata extraction for videos |
| 🔗 **URL Support** | Analyze images from 20+ platforms |
| 🔍 **EXIF Analysis** | Camera model, date/time, software |
| 🔐 **File Hashing** | MD5, SHA-1, SHA-256 |
| 📝 **Text Extraction** | Embedded URLs, emails, locations |
| 📁 **Batch Processing** | Scan entire directories |

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/keiz7en/owlshook.git
cd owlshook

# Make executable
chmod +x owlshook

# Install dependencies
sudo apt install exiftool

# Add to PATH (optional)
sudo ln -sf $(pwd)/owlshook /usr/local/bin/owlshook
```

---

## 🚀 Usage

### Basic Commands

```bash
# Show help
./owlshook --help

# Show version
./owlshook --version

# Show OSINT techniques guide
./owlshook guide
```

### Analyze Local Files

```bash
# Full file analysis with all metadata
./owlshook trace photo.jpg

# Extract GPS and EXIF data
./owlshook gps photo.jpg

# Generate file hashes
./owlshook hash photo.jpg

# Extract embedded strings
./owlshook strings photo.jpg

# Complete scan with all details
./owlshook scan photo.jpg
```

### Analyze URLs

```bash
# Analyze image from any URL
./owlshook trace 'https://example.com/photo.jpg'

# Google Drive (public files)
./owlshook trace 'https://drive.google.com/file/d/FILE_ID/view'

# Google Photos
./owlshook trace 'https://lh3.googleusercontent.com/...'

# Social media
./owlshook trace 'https://instagram.com/p/ABC123/'
./owlshook trace 'https://twitter.com/user/status/123'
./owlshook trace 'https://facebook.com/photo.php?fbid=123'
```

### Batch Processing

```bash
# Scan entire directory
./owlshook dir /path/to/photos/

# Export to JSON
./owlshook scan photo.jpg --output report.json
```

### Geolocation Tools

```bash
# Multi-method location finder
./owlshook geolocate photo.jpg

# Show all OSINT techniques
./owlshook guide
```

---

## 🌐 Supported Platforms

| Platform | GPS | Server Geo | Notes |
|----------|-----|------------|-------|
| **Phone/Camera Photos** | ✅ Full | N/A | Best source for GPS |
| **Google Drive** | ✅ If public | ✅ | Must share "Anyone with link" |
| **Google Photos** | ✅ Text | ✅ | Extracts from description |
| **Flickr (Original)** | ✅ Full | ✅ | Download original size |
| **Wikimedia** | ✅ May work | ✅ | Check image description |
| **Instagram** | ❌ Stripped | ✅ | Server location available |
| **Facebook** | ❌ Stripped | ✅ | Server location available |
| **Twitter/X** | ❌ Stripped | ✅ | Server location available |
| **Reddit** | ❌ Stripped | ✅ | Server location available |
| **Imgur** | ❌ Stripped | ✅ | Server location available |
| **TikTok** | ❌ Stripped | ✅ | Server location available |
| **LinkedIn** | ❌ Stripped | ✅ | Server location available |
| **YouTube** | ❌ Stripped | ✅ | Thumbnail analysis |
| **Dropbox** | ✅ May work | ✅ | Check file metadata |
| **OneDrive** | ✅ May work | ✅ | Check file metadata |
| **Pinterest** | ❌ Stripped | ✅ | Server location available |
| **DeviantArt** | ❌ Stripped | ✅ | Server location available |

---

## 📍 Location Extraction Methods

### 1. GPS Metadata (Direct)
```
*** LOCATION FOUND ***
Latitude  : 43.150269
Longitude : -80.185883
Maps      : https://maps.google.com/?q=43.150269,-80.185883
```

### 2. Text Location (From EXIF)
```
*** LOCATION FOUND (from text) ***
Location  : BGMEA University Dhaka, Bangladesh
```

### 3. Server Geolocation (IP-based)
```
*** SERVER LOCATION ***
(Approximate - from hosting server)
Server IP   : 49.12.22.106
City       : Falkenstein
Region     : Saxony
Country    : Germany
Organization: Hetzner Online GmbH
ISP       : Hetzner Online GmbH
Maps       : https://maps.google.com/?q=50.4777,12.3649
```

### 4. Timezone Analysis
```
--- TIMEZONE ANALYSIS ---
GPS Time           : 2020:03:27 00:13:57Z
GPS Timezone       : UTC-5
```

---

## 🤖 AI Detection

The tool automatically detects AI-generated content:

```
--- AI ANALYSIS ---
✓ AI GENERATED: NO
Likely real human content
```

or

```
--- AI ANALYSIS ---
⚠ AI GENERATED: YES
Confidence: HIGH
Detection signs:
  • EXIF contains 'dall-e' in Software
  • Found 'stable diffusion' in strings
```

**Supported AI Tools:**
- DALL-E, Midjourney, Stable Diffusion
- Flux, Craiyon, NightCafe, DreamStudio
- Leonardo, Runway, Sora, Pika, Kling
- Hailuo, MiniMax, Luma
- Deepfake, Adobe Firefly, Canva AI

---

## 🎬 Video Analysis

Full metadata extraction for video files:

```
--- VIDEO METADATA ---
Duration    : 2m 34s
Resolution  : 1920x1080
Video Codec : h264
Audio Codec : aac
FPS         : 30/1
Bitrate     : 2500000
```

**Supported Formats:**
- MP4, AVI, MOV, MKV, WebM
- FLV, WMV, M4V, 3GP, TS

---

## ⏰ Timezone Analysis

Predicts location from timestamp:

```
--- TIMEZONE ANALYSIS ---
Upload Time (UTC)  : 2023-11-29 16:39:03 UTC
Upload Time (Local): 2023-11-29 22:09:03
Timezone           : UTC+6
Possible Regions   : Dhaka, Almaty, Omsk
```

---

## 🔧 Technical Details

### GPS Tag Parsing
```python
# Reads from EXIF:
# - GPS GPSLatitude / GPSLongitude
# - GPS GPSLatitudeRef / GPSLongitudeRef
# - GPS GPSDateTime

# Converts DMS to Decimal:
# 43 deg 9' 0.97" N → 43.150269
# 80 deg 11' 9.18" W → -80.185883
```

### Server Geolocation
```python
# Uses ip-api.com and ipinfo.io
# Resolves hostname → IP → City/Country
# Calculates timezone from longitude
```

### AI Detection
```python
# Checks:
# - EXIF metadata for AI keywords
# - File strings for tool names
# - Camera manufacturer detection
# - Software analysis
```

---

## 📁 Project Structure

```
owlshook/
├── owlshook              # Main CLI entry point
├── tracer.py             # GPS extraction, EXIF, hashes, URL resolution
├── file_inspector.py     # Comprehensive file analysis
├── url_inspector.py      # URL download and analysis
├── metadata_extractor.py # GPS extractor with exifread fallback
├── geolocate.py          # Multi-method location finder
├── geolocation_guide.py  # OSINT techniques guide
├── README.md             # This file
└── LICENSE               # MIT License
```

---

## 🛠️ Dependencies

```bash
# Required
sudo apt install exiftool

# Optional (for enhanced features)
pip install exifread Pillow

# For video analysis
sudo apt install ffmpeg
```

---

## 📋 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `trace` | Full analysis with GPS/EXIF | `owlshook trace photo.jpg` |
| `gps` | Extract GPS coordinates only | `owlshook gps photo.jpg` |
| `scan` | Complete file scan | `owlshook scan photo.jpg` |
| `hash` | Generate file hashes | `owlshook hash photo.jpg` |
| `strings` | Extract embedded text | `owlshook strings file.exe` |
| `dir` | Scan entire directory | `owlshook dir /path/` |
| `url` | Analyze URL/image | `owlshook url 'https://...'` |
| `geolocate` | Multi-method location | `owlshook geolocate photo.jpg` |
| `guide` | Show OSINT techniques | `owlshook guide` |

---

## 🔍 OSINT Techniques

Run `owlshook guide` to see all 10 geolocation methods:

1. **EXIF GPS** - Direct coordinates from metadata
2. **Reverse Image Search** - Find original source
3. **Visual Analysis** - Signs, landmarks, text
4. **Shadow Analysis** - Determine time/hemisphere
5. **Social Context** - Captions, hashtags, profile
6. **URL Metadata** - Page tags with coordinates
7. **Camera Fingerprint** - Match specific camera
8. **Weather Data** - Cross-reference conditions
9. **Image Forensics** - ELA, compression analysis
10. **Server Geolocation** - IP-based location

---

## ⚠️ Privacy Notice

**This tool is for educational and authorized forensic use only.**

- Always obtain proper authorization before analyzing others' images
- Respect privacy laws in your jurisdiction
- GPS data is sensitive personal information
- Server geolocation is approximate (city-level)

---

## 🐛 Troubleshooting

### "Command not found"
```bash
# Use relative path
./owlshook --help

# Or add to PATH
export PATH=$PATH:$(pwd)
```

### "No GPS location found"
- Social media platforms strip GPS data
- Try original photos from phone/camera
- Use `owlshook geolocate` for alternative methods

### "exiftool not found"
```bash
sudo apt install exiftool
```

### Google Drive download fails
- Make sure file is shared publicly
- Click "Share" → "Anyone with link"
- Download manually, then analyze

---

## 📄 License

MIT License - For educational and research purposes.

---

## 👤 Author

**keiz7en** - [GitHub](https://github.com/keiz7en)

Developed for OSINT and forensic research.

**Use responsibly and ethically.** 🦉
