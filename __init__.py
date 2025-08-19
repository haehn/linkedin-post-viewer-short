"""
LinkedIn Post Viewer Backend

A backend service for scraping and displaying LinkedIn posts from public profiles.
Provides a FastAPI REST API interface for the frontend application.

Main Components:
- viewer.py: Selenium-based LinkedIn scraper
- main.py: FastAPI application with REST endpoints
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main components for easy access
from .main import app
from .viewer import (
    setup_driver,
    login_linkedin,
    scrape_posts,
    extract_post_content,
    construct_posts_url
)

# Package metadata
__all__ = [
    "app",
    "setup_driver", 
    "login_linkedin",
    "scrape_posts",
    "extract_post_content",
    "construct_posts_url"
]