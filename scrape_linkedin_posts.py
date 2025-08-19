#!/usr/bin/env python3
"""
LinkedIn Post Scraper with Timestamps
A single-file LinkedIn post scraper that extracts posts from multiple profiles/pages
and outputs structured JSON data with timestamps for proper ordering.

Usage:
    python scrape_linkedin_posts.py -c "https://www.linkedin.com/in/haehn/recent-activity/all/,https://www.linkedin.com/company/100647235/admin/page-posts/published/" -o posts.json

Requirements:
    pip install selenium beautifulsoup4 requests argparse
"""

import argparse
import json
import time
import getpass
import sys
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# BeautifulSoup imports
from bs4 import BeautifulSoup


def setup_driver(headless=True):
    """Setup Chrome driver with anti-detection tweaks."""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    if headless:
        options.add_argument("--headless=new")

    # Try to find chromedriver in common locations
    chromedriver_paths = [
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
        "./chromedriver",
        "chromedriver"
    ]
    
    service = None
    for path in chromedriver_paths:
        if os.path.exists(path):
            service = Service(executable_path=path)
            break
    
    if not service:
        # Try without specifying path (assumes chromedriver is in PATH)
        service = Service()

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        print("Please ensure chromedriver is installed and in your PATH")
        print("Download from: https://chromedriver.chromium.org/")
        sys.exit(1)


def login_linkedin(driver, email=None, password=None):
    """Login to LinkedIn with credentials."""
    driver.get("https://www.linkedin.com/login")
    
    if not email:
        email = input("LinkedIn Email: ")
    if not password:
        password = getpass.getpass("LinkedIn Password: ")

    try:
        username_input = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "username"))
        )
        password_input = driver.find_element(By.ID, "password")

        username_input.clear()
        username_input.send_keys(email)
        password_input.clear()
        password_input.send_keys(password)

        try:
            sign_in_button = driver.find_element(By.XPATH, '//button[@type="submit"]')
        except NoSuchElementException:
            sign_in_button = driver.find_element(
                By.XPATH, '//button[contains(text(), "Sign in")]'
            )

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(sign_in_button))
        sign_in_button.click()

        try:
            WebDriverWait(driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.feed-container-theme')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'main#main-content'))
                )
            )
            print("✓ Successfully logged in to LinkedIn")
            return True
        except TimeoutException:
            print("Login submitted, but may require CAPTCHA/2FA.")
            print("Please complete verification in the browser...")
            input("Press Enter here after completing verification: ")
            return True

    except Exception as e:
        print(f"Login failed: {e}")
        return False


def normalize_linkedin_url(url):
    """Convert any LinkedIn profile URL to the posts activity URL."""
    url = url.rstrip('/')
    
    # Handle different LinkedIn URL formats
    if '/recent-activity' in url:
        if not url.endswith('/all/'):
            base_url = url.split('/recent-activity')[0]
            return f"{base_url}/recent-activity/all/"
        return url
    elif '/company/' in url:
        if '/admin/page-posts' in url:
            return url
        # For company pages, try to get posts feed
        company_id = url.split('/company/')[1].split('/')[0]
        return f"https://www.linkedin.com/company/{company_id}/posts/"
    else:
        # Regular profile URL
        return f"{url}/recent-activity/all/"


def parse_relative_time(time_text):
    """Parse LinkedIn's relative time format (e.g., '2d', '1w', '3mo') to ISO timestamp."""
    if not time_text:
        return datetime.now().isoformat()
    
    time_text = time_text.lower().strip()
    now = datetime.now()
    
    # Handle "now" or "just now"
    if 'now' in time_text:
        return now.isoformat()
    
    # Extract number and unit
    match = re.match(r'(\d+)\s*([a-z]+)', time_text)
    if not match:
        return now.isoformat()
    
    amount = int(match.group(1))
    unit = match.group(2)
    
    # Convert to timedelta
    if unit.startswith('s'):  # seconds
        delta = timedelta(seconds=amount)
    elif unit.startswith('m') and 'mo' not in unit:  # minutes
        delta = timedelta(minutes=amount)
    elif unit.startswith('h'):  # hours
        delta = timedelta(hours=amount)
    elif unit.startswith('d'):  # days
        delta = timedelta(days=amount)
    elif unit.startswith('w'):  # weeks
        delta = timedelta(weeks=amount)
    elif 'mo' in unit:  # months
        delta = timedelta(days=amount * 30)  # Approximate
    elif unit.startswith('y'):  # years
        delta = timedelta(days=amount * 365)  # Approximate
    else:
        return now.isoformat()
    
    # Subtract from current time
    post_time = now - delta
    return post_time.isoformat()


def extract_post_timestamp(post_element):
    """Extract timestamp from a post element."""
    timestamp_selectors = [
        'time',
        '.update-components-actor__sub-description time',
        '.feed-shared-actor__sub-description time',
        '.update-components-actor__meta time',
        'span.visually-hidden:contains("ago")',
        '.feed-shared-actor__sub-description',
        '.update-components-actor__sub-description'
    ]
    
    for selector in timestamp_selectors:
        try:
            time_elements = post_element.find_elements(By.CSS_SELECTOR, selector)
            for time_element in time_elements:
                # Try datetime attribute first
                datetime_attr = time_element.get_attribute('datetime')
                if datetime_attr:
                    return datetime_attr
                
                # Try title attribute
                title_attr = time_element.get_attribute('title')
                if title_attr and ('ago' in title_attr.lower() or any(c.isdigit() for c in title_attr)):
                    return parse_relative_time(title_attr)
                
                # Try text content
                text = time_element.text.strip()
                if text and ('ago' in text.lower() or any(c.isdigit() for c in text)):
                    return parse_relative_time(text)
                    
        except Exception:
            continue
    
    # Fallback: look for any text that looks like a timestamp
    try:
        all_text = post_element.text
        time_patterns = [
            r'(\d+[smhdw])\s*ago',
            r'(\d+\s*(second|minute|hour|day|week|month|year)s?)\s*ago',
            r'(\d+[smhdw])',
            r'(\d+mo)',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                return parse_relative_time(match.group(1))
                
    except Exception:
        pass
    
    # Ultimate fallback
    return datetime.now().isoformat()


def extract_post_url_from_element(post_element):
    """Extract the original LinkedIn post URL from a post element."""
    try:
        # Try to get URN from data attribute
        urn = post_element.get_attribute("data-urn")
        if urn and "activity:" in urn:
            activity_id = urn.split("activity:")[1]
            return f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
        
        # Try to find permalink in the post
        permalink_selectors = [
            'a[href*="/feed/update/"]',
            'a[href*="activity:"]',
            '.update-components-actor__meta a'
        ]
        
        for selector in permalink_selectors:
            try:
                link = post_element.find_element(By.CSS_SELECTOR, selector)
                href = link.get_attribute('href')
                if href and ('feed/update' in href or 'activity:' in href):
                    return href
            except NoSuchElementException:
                continue
                
        return None
        
    except Exception as e:
        print(f"Error extracting post URL: {e}")
        return None


def extract_media_urls(post_element):
    """Extract media URLs from a post element."""
    media_urls = []
    
    try:
        # Find all images in the post
        images = post_element.find_elements(By.TAG_NAME, 'img')
        for img in images:
            src = img.get_attribute('src')
            alt = img.get_attribute('alt') or ''
            classes = img.get_attribute('class') or ''
            
            # Filter out profile pictures, avatars, and reaction icons
            if src and 'media.licdn.com/dms' in src:
                skip_terms = ['avatar', 'profile', 'entity-photo', 'presence-entity', 'actor', 'reactions-icon']
                if not any(term in classes.lower() + alt.lower() for term in skip_terms):
                    if src not in media_urls:
                        media_urls.append(src)
        
        # Find all videos in the post
        videos = post_element.find_elements(By.TAG_NAME, 'video')
        for video in videos:
            src = video.get_attribute('src')
            if src and src not in media_urls:
                media_urls.append(src)
                
    except Exception as e:
        print(f"Error extracting media: {e}")
    
    return media_urls


def extract_author_info(post_element):
    """Extract author information from a post element."""
    author_info = {
        'name': '',
        'profile_url': '',
        'title': '',
        'avatar_url': ''
    }
    
    try:
        # Extract author name
        name_selectors = [
            '.update-components-actor__name',
            '.feed-shared-actor__name',
            '.update-components-actor__title'
        ]
        
        for selector in name_selectors:
            try:
                name_element = post_element.find_element(By.CSS_SELECTOR, selector)
                author_info['name'] = name_element.text.strip()
                if author_info['name']:
                    break
            except NoSuchElementException:
                continue
        
        # Extract profile URL
        try:
            profile_link = post_element.find_element(By.CSS_SELECTOR, '.update-components-actor__name a, .feed-shared-actor__name a')
            author_info['profile_url'] = profile_link.get_attribute('href')
        except NoSuchElementException:
            pass
        
        # Extract profile picture/avatar
        avatar_selectors = [
            '.update-components-actor__avatar img',
            '.feed-shared-actor__avatar img',
            '.update-components-actor img[alt*="photo"]',
            '.feed-shared-actor img[alt*="photo"]',
            'img.presence-entity__image',
            'img.EntityPhoto-circle-3'
        ]
        
        for selector in avatar_selectors:
            try:
                avatar_img = post_element.find_element(By.CSS_SELECTOR, selector)
                avatar_src = avatar_img.get_attribute('src')
                if avatar_src and 'profile' in avatar_src.lower():
                    author_info['avatar_url'] = avatar_src
                    break
            except NoSuchElementException:
                continue
        
        # Extract title/description
        title_selectors = [
            '.update-components-actor__description',
            '.feed-shared-actor__description'
        ]
        
        for selector in title_selectors:
            try:
                title_element = post_element.find_element(By.CSS_SELECTOR, selector)
                author_info['title'] = title_element.text.strip()
                if author_info['title']:
                    break
            except NoSuchElementException:
                continue
                
    except Exception as e:
        print(f"Error extracting author info: {e}")
    
    return author_info


def extract_post_content(post_element, post_index):
    """Extract content from a single post element."""
    post_data = {
        'original': '',
        'text': '',
        'media': [],
        'timestamp': '',
        'author': {
            'name': '',
            'profile_url': '',
            'title': ''
        }
    }
    
    try:
        # Extract post URL
        post_data['original'] = extract_post_url_from_element(post_element) or ''
        
        # Extract timestamp
        post_data['timestamp'] = extract_post_timestamp(post_element)
        
        # Extract author information
        post_data['author'] = extract_author_info(post_element)
        
        # Extract text content
        content_selectors = [
            'span.break-words',
            '.feed-shared-text',
            '.update-components-text',
            '.attributed-text-segment-list__content',
            '[data-attributed-text]',
            '.feed-shared-update-v2__description-wrapper span'
        ]
        
        for selector in content_selectors:
            try:
                content_element = post_element.find_element(By.CSS_SELECTOR, selector)
                text = content_element.text.strip()
                if text:
                    post_data['text'] = text
                    break
            except NoSuchElementException:
                continue
        
        # Extract media URLs
        post_data['media'] = extract_media_urls(post_element)
        
        print(f"  Post {post_index}: {len(post_data['text'])} chars, {len(post_data['media'])} media, {post_data['timestamp'][:10]}")
        
    except Exception as e:
        print(f"  Error extracting post {post_index}: {e}")
    
    return post_data


def scrape_linkedin_channel(driver, channel_url, max_posts=50, scroll_count=10):
    """Scrape posts from a single LinkedIn channel/profile."""
    print(f"\nScraping: {channel_url}")
    
    # Normalize the URL
    posts_url = normalize_linkedin_url(channel_url)
    print(f"Visiting: {posts_url}")
    
    driver.get(posts_url)
    
    # Wait for posts to load
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.feed-shared-update-v2, .artdeco-empty-state, .org-page-navigation-module__links')
            )
        )
    except TimeoutException:
        print("  ⚠ Posts didn't load within timeout")
        return []

    # Check if profile has no visible posts
    if driver.find_elements(By.CSS_SELECTOR, '.artdeco-empty-state'):
        print("  ⚠ Profile appears to have no visible posts or is private")
        return []

    # Scroll to load more posts
    print(f"  Scrolling {scroll_count} times to load posts...")
    for i in range(scroll_count):
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)
        if i % 3 == 0:
            print(f"    Scroll {i+1}/{scroll_count}")

    # Find all post elements
    post_selectors = [
        'div.feed-shared-update-v2',
        'div[data-urn*="activity"]',
        '.update-components-actor'
    ]

    all_posts = []
    for selector in post_selectors:
        posts = driver.find_elements(By.CSS_SELECTOR, selector)
        if posts:
            all_posts = posts
            print(f"  Found {len(posts)} post elements using selector: {selector}")
            break

    if not all_posts:
        print("  ⚠ No posts found")
        return []

    # Extract content from posts
    extracted_posts = []
    posts_to_process = min(len(all_posts), max_posts)
    
    print(f"  Processing {posts_to_process} posts...")
    
    for i, post_element in enumerate(all_posts[:posts_to_process]):
        try:
            post_data = extract_post_content(post_element, i + 1)
            
            # Only include posts with content or media
            if post_data['text'].strip() or post_data['media']:
                extracted_posts.append(post_data)
            else:
                print(f"    Skipping empty post {i+1}")
                
        except Exception as e:
            print(f"    Error processing post {i+1}: {e}")
            continue

    print(f"  ✓ Successfully extracted {len(extracted_posts)} posts")
    return extracted_posts


def main():
    """Main function to handle CLI arguments and orchestrate scraping."""
    parser = argparse.ArgumentParser(
        description='LinkedIn Post Scraper - Extract posts from LinkedIn profiles/pages with timestamps',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python scrape_linkedin_posts.py -c "https://www.linkedin.com/in/username/" -o posts.json
  python scrape_linkedin_posts.py -c "url1,url2,url3" -o output.json --max-posts 30
  python scrape_linkedin_posts.py -c "https://www.linkedin.com/company/123/" -o company_posts.json
        '''
    )
    
    parser.add_argument(
        '-c', '--channels',
        required=True,
        help='Comma-separated list of LinkedIn URLs to scrape'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='posts.json',
        help='Output JSON file (default: posts.json)'
    )
    
    parser.add_argument(
        '--max-posts',
        type=int,
        default=50,
        help='Maximum posts to extract per channel (default: 50)'
    )
    
    parser.add_argument(
        '--scrolls',
        type=int,
        default=10,
        help='Number of scrolls to load posts (default: 10)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    
    parser.add_argument(
        '--email',
        help='LinkedIn email (will prompt if not provided)'
    )
    
    parser.add_argument(
        '--password',
        help='LinkedIn password (will prompt if not provided)'
    )

    args = parser.parse_args()

    # Parse channel URLs
    channel_urls = [url.strip() for url in args.channels.split(',') if url.strip()]
    
    if not channel_urls:
        print("Error: No valid channel URLs provided")
        sys.exit(1)

    print(f"LinkedIn Post Scraper v2.0 (with timestamps)")
    print(f"Channels to scrape: {len(channel_urls)}")
    print(f"Max posts per channel: {args.max_posts}")
    print(f"Output file: {args.output}")
    print(f"Headless mode: {args.headless}")

    # Setup driver
    driver = setup_driver(headless=args.headless)
    
    try:
        # Login to LinkedIn
        if not login_linkedin(driver, args.email, args.password):
            print("Failed to login to LinkedIn")
            sys.exit(1)
        
        # Scrape all channels
        all_posts = []
        
        for i, channel_url in enumerate(channel_urls):
            print(f"\n--- Channel {i+1}/{len(channel_urls)} ---")
            
            posts = scrape_linkedin_channel(
                driver, 
                channel_url, 
                max_posts=args.max_posts, 
                scroll_count=args.scrolls
            )
            
            all_posts.extend(posts)
        
        # Sort posts by timestamp (newest first)
        all_posts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Convert to numbered dictionary format
        numbered_posts = {}
        for i, post in enumerate(all_posts):
            numbered_posts[i] = post
        
        # Save to JSON file
        print(f"\n--- Saving Results ---")
        
        if numbered_posts:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(numbered_posts, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Successfully saved {len(numbered_posts)} posts to {args.output}")
            
            # Print summary
            total_media = sum(len(post.get('media', [])) for post in numbered_posts.values())
            total_text_length = sum(len(post.get('text', '')) for post in numbered_posts.values())
            
            print(f"\nSUMMARY:")
            print(f"  Total posts: {len(numbered_posts)}")
            print(f"  Total media files: {total_media}")
            print(f"  Total text length: {total_text_length} characters")
            print(f"  Average post length: {total_text_length // len(numbered_posts) if numbered_posts else 0} characters")
            print(f"  Posts sorted by: timestamp (newest first)")
            
        else:
            print("⚠ No posts were extracted")
            # Create empty JSON file
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        
    except Exception as e:
        print(f"\nError during scraping: {e}")
        sys.exit(1)
        
    finally:
        try:
            driver.quit()
        except:
            pass
        print("\n✓ Browser closed")


if __name__ == "__main__":
    main()