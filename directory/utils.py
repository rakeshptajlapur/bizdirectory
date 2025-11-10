# directory/utils.py
import re
from urllib.parse import urlparse, parse_qs

def extract_youtube_video_id(url):
    """
    Extract YouTube video ID from various YouTube URL formats
    Supports:
    - https://youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtu.be/dQw4w9WgXcQ
    - https://youtube.com/embed/dQw4w9WgXcQ
    - https://youtube.com/v/dQw4w9WgXcQ
    """
    if not url:
        return None
    
    # YouTube video ID is 11 characters long
    video_id_pattern = r'[a-zA-Z0-9_-]{11}'
    
    # Different YouTube URL patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_youtube_embed_url(url):
    """
    Convert YouTube URL to embeddable format
    Returns: https://www.youtube.com/embed/VIDEO_ID
    """
    video_id = extract_youtube_video_id(url)
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}"
    return None