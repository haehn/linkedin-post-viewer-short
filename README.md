# LinkedIn Post Scraper & Viewer

A complete solution for scraping LinkedIn posts and viewing them in a beautiful web interface. This tool extracts posts from LinkedIn profiles/company pages with timestamps, media, and author information, then displays them in a clean, responsive viewer.

## Features

-  **Smart Scraping**: Extract posts from LinkedIn profiles and company pages
-  **Timestamp Support**: Posts are automatically sorted by date (newest first)
-  **Media Extraction**: Downloads and displays images from posts
-  **Author Information**: Captures profile details and avatars
-  **Search Functionality**: Filter posts by content, author, or keywords
-  **Responsive Design**: Works perfectly on desktop and mobile
-  **Statistics**: View post counts, media files, and content analytics

## Linux Installation & Setup

### Prerequisites

Make sure you have Python 3.8+ installed:

```bash
python3 --version
# If not installed: sudo apt update && sudo apt install python3 python3-pip
```

### 1. Clone or Download

```bash
# If you have git:
git clone <your-repo-url>
cd linkedin-scraper

# Or download and extract the files to a folder
```

### 2. Install Python Dependencies

```bash
# Install required Python packages
pip3 install -r requirements.txt

# Alternative if pip3 doesn't work:
python3 -m pip install -r requirements.txt
```

### 3. Install Chrome and ChromeDriver

Your current script requires manual ChromeDriver installation. Here are the steps:

#### Install Chrome Browser

**Ubuntu/Debian:**
```bash
# Method 1: Using Google's repository (recommended)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable
```


#### Install ChromeDriver

**Option A: Using Package Manager (Easiest)**
```bash
# Ubuntu/Debian:
sudo apt install chromium-chromedriver
```

**Option B: Manual Download (Latest Version)**
```bash
# Get the latest ChromeDriver version
LATEST=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE")
echo "Latest ChromeDriver version: $LATEST"

# Download for Linux
wget "https://chromedriver.storage.googleapis.com/$LATEST/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip

# Install to system PATH
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

# Clean up
rm chromedriver_linux64.zip
```

**Option C: Install in Project Directory**
```bash
# Download to current directory (no sudo needed)
LATEST=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE")
wget "https://chromedriver.storage.googleapis.com/$LATEST/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
chmod +x chromedriver
rm chromedriver_linux64.zip

# The script will find it in the current directory
```

### 4. Verify Installation

```bash
# Test Chrome
google-chrome --version

# Test ChromeDriver
chromedriver --version
# Should show version like: ChromeDriver 119.0.6045.105
```

## Usage

### Step 1: Scrape LinkedIn Posts

```bash
# Basic usage - scrape a single profile
python3 scrape_linkedin_posts.py -c "https://www.linkedin.com/in/username/" -o posts.json
python3 scrape_linkedin_posts.py -c "https://www.linkedin.com/company/123/" -o posts.json
python3 scrape_linkedin_posts.py -c "https://www.linkedin.com/in/username/,https://www.linkedin.com/company/123/posts/?feedView=all" -o posts.json

# Scrape multiple profiles/pages
python3 scrape_linkedin_posts.py -c "https://www.linkedin.com/in/user1/,https://www.linkedin.com/company/123/" -o posts.json

# Advanced options
python3 scrape_linkedin_posts.py \
  -c "https://www.linkedin.com/in/username/" \
  -o my_posts.json \
  --max-posts 100 \
  --scrolls 15 \
  --headless
```

#### Command Line Options

- `-c, --channels`: LinkedIn URLs (comma-separated)
- `-o, --output`: Output JSON file (default: posts.json)
- `--max-posts`: Maximum posts per profile (default: 50)
- `--scrolls`: Number of scrolls to load content (default: 10)
- `--headless`: Run browser without GUI (faster)
- `--email`: LinkedIn email (optional, will prompt)
- `--password`: LinkedIn password (optional, will prompt)

#### Supported URL Formats

```bash
# Profile recent activity (recommended):
https://www.linkedin.com/in/username/recent-activity/all/

# Regular profile (auto-converted):
https://www.linkedin.com/in/username/

# Company pages:
https://www.linkedin.com/company/company-id/posts/
https://www.linkedin.com/company/company-id/

# Both
python3 scrape_linkedin_posts.py -c "https://www.linkedin.com/in/username/,https://www.linkedin.com/company/123/posts/?feedView=all" -o posts.json
```

### Step 2: View Posts

#### Option A: Simple File Viewing

```bash
# Open with default browser
open linkedin_viewer.html

# Or specifically with Chrome (if installed)
open -a "Google Chrome" linkedin_viewer.html
```

Then use the "Load JSON File" button to upload your `posts.json`.

#### Option B: Local Web Server (Recommended)

```bash
# Start a simple HTTP server
python3 -m http.server 8000

# Then open in browser (in the second terminal)
open http://localhost:8000/linkedin_viewer.html
```

This method works better for loading JSON files and avoids browser security restrictions.

#### Option C: With Custom Data File

Place your `posts.json` in the same directory and open:
```bash
firefox "linkedin_viewer.html?data=posts.json"
```

## Example Workflow

Here's a complete example of scraping and viewing posts:

```bash
# 1. Scrape posts from Daniel Haehn's profile
python3 scrape_linkedin_posts.py \
  -c "https://www.linkedin.com/in/haehn/" \
  -o daniel_posts.json \
  --max-posts 50 \
  --headless

# 2. Start local server
python3 -m http.server 8000 &

# 3. Open viewer in browser
firefox http://localhost:8000/linkedin_viewer.html

# 4. Load the JSON file using the interface
```

## Troubleshooting

### Common Issues

**ChromeDriver issues:**
```bash
# Check if ChromeDriver is in PATH
which chromedriver

# If not found, install it:
sudo apt install chromium-chromedriver  # Ubuntu/Debian
# or download from https://chromedriver.chromium.org/

# Make sure ChromeDriver version matches Chrome version
google-chrome --version
chromedriver --version
```

**Version mismatch between Chrome and ChromeDriver:**
```bash
# Update Chrome
sudo apt update && sudo apt upgrade google-chrome-stable

# Download matching ChromeDriver version from:
# https://chromedriver.chromium.org/downloads
```

**Permission issues:**
```bash
# Make sure ChromeDriver is executable
sudo chmod +x /usr/local/bin/chromedriver
# or if in project directory:
chmod +x ./chromedriver
```

**Login issues:**
- LinkedIn may require CAPTCHA or 2FA
- The script will pause and wait for manual completion
- Use `--headless` flag carefully as you won't see CAPTCHA prompts

**Permission denied:**
```bash
# Make script executable
chmod +x scrape_linkedin_posts.py

# Or run with python3 explicitly
python3 scrape_linkedin_posts.py [options]
```

**Browser crashes:**
```bash
# Add more memory if running in limited environments
export CHROME_OPTS="--no-sandbox --disable-dev-shm-usage"
```

**No posts found:**
- Profile might be private or have no recent posts
- Try increasing `--scrolls` parameter
- Check if LinkedIn URL is correct

### File Permissions

```bash
# Make sure all files are readable
chmod 644 *.html *.json *.py requirements.txt
chmod +x scrape_linkedin_posts.py
```

## Advanced Features

### Filtering and Search

The web viewer includes:
- **Real-time search**: Filter posts by text, author, or keywords
- **Statistics**: View total posts, media files, character counts
- **Media viewer**: Click images to view in full-screen modal
- **Responsive design**: Works on mobile and desktop

### JSON Data Format

The scraper outputs structured JSON:

```json
{
  "0": {
    "original": "https://www.linkedin.com/feed/update/urn:li:activity:123...",
    "text": "Post content here...",
    "media": ["https://media.licdn.com/dms/image/..."],
    "timestamp": "2025-08-18T15:47:15.222366",
    "author": {
      "name": "Author Name",
      "profile_url": "https://www.linkedin.com/in/author/",
      "title": "Job Title",
      "avatar_url": "https://media.licdn.com/..."
    }
  }
}
```

### Automation Scripts

Create a shell script for regular scraping:

```bash
#!/bin/bash
# save as scrape_daily.sh

DATE=$(date +%Y%m%d)
python3 scrape_linkedin_posts.py \
  -c "https://www.linkedin.com/in/yourprofile/" \
  -o "posts_$DATE.json" \
  --max-posts 20 \
  --headless

echo "Posts saved to posts_$DATE.json"
```

```bash
chmod +x scrape_daily.sh
./scrape_daily.sh
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool.

## License

This project is for educational and personal use. 
