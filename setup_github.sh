#!/bin/bash
# OwlsHook - GitHub Repository Setup Script
# Run this to create and push to GitHub

echo "🦉 OwlsHook - GitHub Repository Setup"
echo "======================================"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not found!"
    echo "Install it: sudo apt install gh"
    echo "Or visit: https://cli.github.com/"
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "❌ Not logged in to GitHub!"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI ready"
echo ""

# Create repository
echo "📦 Creating repository..."
gh repo create owlshook \
    --public \
    --description "Professional OSINT & Digital Forensics Toolkit - GPS extraction, AI detection, server geolocation, video analysis" \
    --source . \
    --remote origin \
    --push \
    -- \
    "cybersecurity" \
    "osint" \
    "forensics" \
    "digital-forensics" \
    "metadata" \
    "exif" \
    "gps" \
    "image-analysis" \
    "video-analysis" \
    "ai-detection" \
    "geolocation" \
    "python" \
    "cli-tool" \
    "infosec" \
    "penetration-testing" \
    "security-tools" \
    "investigation" \
    "threat-intelligence" \
    "incident-response" \
    "digital-investigation"

echo ""
echo "✅ Repository created and pushed!"
echo ""
echo "🌐 View at: https://github.com/keiz7en/owlshook"
echo ""
echo "📋 Topics added:"
echo "   cybersecurity, osint, forensics, digital-forensics,"
echo "   metadata, exif, gps, image-analysis, video-analysis,"
echo "   ai-detection, geolocation, python, cli-tool, infosec,"
echo "   penetration-testing, security-tools, investigation,"
echo "   threat-intelligence, incident-response, digital-investigation"
echo ""
echo "🏷️  Tags:"
echo "   #cybersecurity #osint #forensics #metadata #exif"
echo "   #gps #imageanalysis #videanalysis #aiedetection"
echo "   #geolocation #python #clitool #infosec #security"
echo ""
echo "🦉 OwlsHook is now live!"
