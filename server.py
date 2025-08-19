#!/usr/bin/env python3
"""
FastAPI Server for LinkedIn Post Viewer
Serves the static HTML viewer and provides API endpoints for post data.

Usage:
    pip install fastapi uvicorn python-multipart
    python server.py
    
    # Or with uvicorn directly:
    uvicorn server:app --reload --host 0.0.0.0 --port 8000
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="LinkedIn Post Viewer API",
    description="API for viewing and managing LinkedIn posts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATA_DIR = Path("data")
UPLOADS_DIR = Path("uploads")
STATIC_DIR = Path("static")

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Default posts file
DEFAULT_POSTS_FILE = DATA_DIR / "posts.json"

# In-memory storage for posts (you could use a database instead)
posts_cache: Dict[str, Any] = {}


def load_posts_from_file(file_path: Path) -> Dict[str, Any]:
    """Load posts from a JSON file."""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading posts from {file_path}: {e}")
    return {}


def save_posts_to_file(posts: Dict[str, Any], file_path: Path) -> bool:
    """Save posts to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving posts to {file_path}: {e}")
        return False


def sort_posts_by_timestamp(posts: Dict[str, Any]) -> Dict[str, Any]:
    """Sort posts by timestamp (newest first) and renumber them."""
    if not posts:
        return {}
    
    # Convert to list and sort
    posts_list = [(k, v) for k, v in posts.items()]
    posts_list.sort(
        key=lambda x: x[1].get('timestamp', ''),
        reverse=True
    )
    
    # Renumber posts
    sorted_posts = {}
    for i, (_, post) in enumerate(posts_list):
        sorted_posts[str(i)] = post
    
    return sorted_posts


# Load default posts on startup
posts_cache = load_posts_from_file(DEFAULT_POSTS_FILE)


@app.get("/", response_class=HTMLResponse)
async def serve_viewer():
    """Serve the main LinkedIn post viewer HTML page."""
    # You can embed the HTML directly or serve from a file
    html_content = """
    <!DOCTYPE html>
    <!-- The complete HTML from the previous artifact would go here -->
    <!-- For brevity, I'm showing just the structure -->
    <html>
    <head>
        <title>LinkedIn Post Viewer</title>
        <!-- CSS and meta tags -->
    </head>
    <body>
        <!-- HTML structure -->
        <script>
            // JavaScript code
        </script>
    </body>
    </html>
    """
    
    # In practice, you'd want to serve this from a file:
    viewer_file = Path("linkedin_viewer.html")
    if viewer_file.exists():
        return FileResponse(viewer_file)
    else:
        return HTMLResponse(content="""
        <h1>LinkedIn Post Viewer</h1>
        <p>Please place the linkedin_viewer.html file in the same directory as this server.</p>
        <p>Or use the API endpoints:</p>
        <ul>
            <li><a href="/api/posts">View posts JSON</a></li>
            <li><a href="/docs">API Documentation</a></li>
        </ul>
        """)


@app.get("/api/posts")
async def get_posts() -> Dict[str, Any]:
    """Get all posts."""
    return {
        "posts": posts_cache,
        "total": len(posts_cache),
        "last_updated": datetime.now().isoformat()
    }


@app.get("/api/posts/{post_id}")
async def get_post(post_id: str) -> Dict[str, Any]:
    """Get a specific post by ID."""
    if post_id not in posts_cache:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "post": posts_cache[post_id],
        "id": post_id
    }


@app.post("/api/posts/upload")
async def upload_posts(file: UploadFile = File(...)):
    """Upload a new posts JSON file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    try:
        # Read and parse the uploaded file
        content = await file.read()
        new_posts = json.loads(content.decode('utf-8'))
        
        # Validate the structure
        if not isinstance(new_posts, dict):
            raise HTTPException(status_code=400, detail="JSON must be an object/dictionary")
        
        # Sort posts by timestamp
        sorted_posts = sort_posts_by_timestamp(new_posts)
        
        # Update cache
        global posts_cache
        posts_cache = sorted_posts
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = UPLOADS_DIR / f"posts_backup_{timestamp}.json"
        save_posts_to_file(posts_cache, backup_file)
        save_posts_to_file(posts_cache, DEFAULT_POSTS_FILE)
        
        return {
            "message": "Posts uploaded successfully",
            "total_posts": len(posts_cache),
            "backup_file": str(backup_file)
        }
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/api/posts/reload")
async def reload_posts():
    """Reload posts from the default file."""
    global posts_cache
    posts_cache = load_posts_from_file(DEFAULT_POSTS_FILE)
    
    return {
        "message": "Posts reloaded from file",
        "total_posts": len(posts_cache)
    }


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get statistics about the posts."""
    if not posts_cache:
        return {
            "total_posts": 0,
            "total_media": 0,
            "total_characters": 0,
            "average_length": 0,
            "posts_with_media": 0,
            "date_range": None
        }
    
    posts = list(posts_cache.values())
    
    total_posts = len(posts)
    total_media = sum(len(post.get('media', [])) for post in posts)
    total_characters = sum(len(post.get('text', '')) for post in posts)
    average_length = total_characters // total_posts if total_posts > 0 else 0
    posts_with_media = sum(1 for post in posts if post.get('media'))
    
    # Find date range
    timestamps = [post.get('timestamp') for post in posts if post.get('timestamp')]
    date_range = None
    if timestamps:
        try:
            dates = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
            date_range = {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat()
            }
        except:
            pass
    
    return {
        "total_posts": total_posts,
        "total_media": total_media,
        "total_characters": total_characters,
        "average_length": average_length,
        "posts_with_media": posts_with_media,
        "date_range": date_range
    }


@app.get("/api/search")
async def search_posts(q: str, limit: Optional[int] = 50) -> Dict[str, Any]:
    """Search posts by text content."""
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    query = q.lower()
    matching_posts = {}
    count = 0
    
    for post_id, post in posts_cache.items():
        if count >= limit:
            break
            
        # Search in text, author name, and author title
        searchable_text = " ".join([
            post.get('text', ''),
            post.get('author', {}).get('name', ''),
            post.get('author', {}).get('title', '')
        ]).lower()
        
        if query in searchable_text:
            matching_posts[post_id] = post
            count += 1
    
    return {
        "query": q,
        "posts": matching_posts,
        "total_found": len(matching_posts),
        "limited_to": limit
    }


@app.get("/api/export")
async def export_posts():
    """Export current posts as a JSON file."""
    if not posts_cache:
        raise HTTPException(status_code=404, detail="No posts to export")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"linkedin_posts_export_{timestamp}.json"
    
    return JSONResponse(
        content=posts_cache,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.get("/posts.json")
async def serve_posts_json():
    """Serve the posts as a JSON file for the frontend."""
    return posts_cache


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_posts": len(posts_cache)
    }


# Serve static files (if you have any)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting LinkedIn Post Viewer Server")
    print("📝 Place your posts.json file in the 'data' directory")
    print("🌐 Server will be available at: http://localhost:8000")
    print("📚 API docs available at: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )