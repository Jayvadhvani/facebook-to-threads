import os
import sys
import json
import time
import requests
import config

# File to store persistent state between runs
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_post.json")

def load_state():
    """Load the last posted Facebook post ID, tokens, and refresh timestamp."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state file: {e}")
    return {"last_fb_post_id": "", "last_token_refresh_time": 0, "threads_access_token": ""}

def save_state(state):
    """Save the current state to last_post.json."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print("State updated successfully in last_post.json")
    except Exception as e:
        print(f"Error saving state file: {e}")

def get_latest_fb_posts():
    """Fetch the latest posts from the Facebook Page."""
    if not config.FB_PAGE_ID or not config.FB_PAGE_ACCESS_TOKEN:
        print("Error: FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN is missing in environment.")
        return []

    # We fetch the feed. We request message (caption), attachments (images), and created_time.
    url = f"https://graph.facebook.com/v20.0/{config.FB_PAGE_ID}/posts"
    params = {
        "fields": "id,message,created_time,attachments{media,media_type,subattachments}",
        "access_token": config.FB_PAGE_ACCESS_TOKEN,
        "limit": 5 # Look at the last 5 posts to handle edge cases
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"Facebook Graph API Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        posts = data.get("data", [])
        print(f"Number of posts retrieved from Facebook: {len(posts)}")
        return posts
    except Exception as e:
        print(f"Error fetching Facebook feed: {e}")
        if 'response' in locals() and response is not None:
            print(f"Facebook API response body: {response.text}")
    return []

def extract_media_urls(fb_post):
    """Extract public image URLs from the Facebook post attachments."""
    media_urls = []
    attachments = fb_post.get("attachments", {}).get("data", [])
    
    for attachment in attachments:
        # Check for multiple images (carousel/album)
        subattachments = attachment.get("subattachments", {}).get("data", [])
        if subattachments:
            for sub in subattachments:
                img_src = sub.get("media", {}).get("image", {}).get("src")
                if img_src:
                    media_urls.append(img_src)
        else:
            # Single image post or link preview post with an image
            img_src = attachment.get("media", {}).get("image", {}).get("src")
            if img_src:
                media_urls.append(img_src)
                
    return media_urls

def refresh_threads_token(current_token, state):
    """
    Refresh the long-lived Threads Access Token if 7 days have passed since the last refresh.
    Saves the refreshed token to state so it gets committed back to the repository.
    """
    current_time = int(time.time())
    seven_days = 7 * 24 * 60 * 60
    
    last_refresh = state.get("last_token_refresh_time", 0)
    if last_refresh > 0 and (current_time - last_refresh < seven_days):
        print("Threads access token is still fresh. Skipping refresh.")
        return current_token

    if not config.THREADS_APP_SECRET:
        print("Warning: THREADS_APP_SECRET is not configured. Cannot refresh token.")
        return current_token

    print("Refreshing Threads long-lived access token...")
    url = "https://graph.threads.net/refresh_access_token"
    params = {
        "grant_type": "th_refresh_token",
        "access_token": current_token
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        res_data = response.json()
        new_token = res_data.get("access_token")
        
        if new_token:
            print("Successfully refreshed Threads token.")
            state["last_token_refresh_time"] = current_time
            state["threads_access_token"] = new_token
            return new_token
    except Exception as e:
        print(f"Error refreshing Threads access token: {e}")
        
    return current_token

def create_threads_container(user_id, token, media_type, text=None, media_url=None, is_carousel_item=False):
    """Helper function to create a Threads media or text container."""
    url = "https://graph.threads.net/v1.0/me/threads"
    payload = {
        "media_type": media_type,
        "access_token": token
    }
    if text:
        payload["text"] = text
    if media_url:
        if media_type == "IMAGE":
            payload["image_url"] = media_url
        elif media_type == "VIDEO":
            payload["video_url"] = media_url
            
    if is_carousel_item:
        payload["is_carousel_item"] = "true"
        
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json().get("id")

def publish_threads_container(user_id, token, creation_id):
    """Publish a created container on Threads."""
    url = "https://graph.threads.net/v1.0/me/threads_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": token
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json().get("id")

def format_caption_with_title_and_hashtags(caption):
    """Extracts the first line (title) and all hashtags from the caption, combining them."""
    if not caption:
        return ""
        
    import re
    lines = [line.strip() for line in caption.split('\n')]
    # Find the first non-empty line
    title = ""
    for line in lines:
        if line:
            title = line
            break
            
    # Extract all hashtags
    hashtags = re.findall(r'#\w+', caption)
    hashtag_str = " ".join(hashtags)
    
    # Combine title and hashtags
    if title and hashtag_str:
        formatted = f"{title}\n\n{hashtag_str}"
    elif title:
        formatted = title
    else:
        formatted = hashtag_str
        
    # Ensure it complies with the 500 character limit
    if len(formatted) > 500:
        formatted = formatted[:497] + "..."
        
    return formatted

def post_to_threads(fb_post, token):
    """Format and post Facebook page content to Threads."""
    user_id = "me"
    if not token:
        print("Error: THREADS_ACCESS_TOKEN is missing.")
        return False

    caption = format_caption_with_title_and_hashtags(fb_post.get("message", ""))
    media_urls = extract_media_urls(fb_post)
    
    try:
        container_id = None
        
        if not media_urls:
            # 1. Text only post
            print("Creating text-only Threads container...")
            container_id = create_threads_container(user_id, token, "TEXT", text=caption)
            
        elif len(media_urls) == 1:
            # 2. Single image post
            print(f"Creating single-image Threads container with image: {media_urls[0]}")
            container_id = create_threads_container(user_id, token, "IMAGE", text=caption, media_url=media_urls[0])
            
        else:
            # 3. Carousel/Multi-image post (limit to 20 per Threads requirements)
            print(f"Creating carousel Threads container with {len(media_urls)} images...")
            carousel_item_ids = []
            
            # Create individual items
            for img_url in media_urls[:20]:
                item_id = create_threads_container(
                    user_id, token, "IMAGE", media_url=img_url, is_carousel_item=True
                )
                carousel_item_ids.append(item_id)
                
            # Create the main carousel container
            url = "https://graph.threads.net/v1.0/me/threads"
            payload = {
                "media_type": "CAROUSEL",
                "children": ",".join(carousel_item_ids),
                "access_token": token
            }
            if caption:
                payload["text"] = caption
                
            response = requests.post(url, data=payload)
            response.raise_for_status()
            container_id = response.json().get("id")
 

        if container_id:
            # Wait a few seconds for processing (recommended by Meta for media posts)
            if media_urls:
                time.sleep(5)
                
            # Publish the post
            print("Publishing container to Threads...")
            publish_id = publish_threads_container(user_id, token, container_id)
            print(f"Successfully posted to Threads! Post ID: {publish_id}")
            return True
            
    except Exception as e:
        print(f"Error publishing to Threads: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response body: {e.response.text}")
            
    return False

def main():
    print("Starting Facebook to Threads Auto Poster...")
    state = load_state()
    
    # Use token from state first (since it refreshes and saves here).
    # Fallback to the environment variable token if state is empty.
    threads_token = state.get("threads_access_token") or config.THREADS_ACCESS_TOKEN
    
    if not threads_token:
        print("Error: THREADS_ACCESS_TOKEN is not available in state or environment variables.")
        sys.exit(1)
        
    # Refresh token if needed
    threads_token = refresh_threads_token(threads_token, state)
    
    # Ensure the token is set in state for future runs
    state["threads_access_token"] = threads_token
        
    # Get latest Facebook Page posts
    posts = get_latest_fb_posts()
    if not posts:
        print("No Facebook posts found or error occurred.")
        save_state(state) # Save potential token refresh updates
        return
        
    last_fb_post_id = state.get("last_fb_post_id")
    
    # Find which posts are new (have not been published yet)
    new_posts = []
    for post in posts:
        if post.get("id") == last_fb_post_id:
            break
        new_posts.append(post)
        
    if not new_posts:
        print("No new posts to publish. Skipping.")
        save_state(state)
        return
        
    print(f"Found {len(new_posts)} new post(s) to publish.")
    
    # Post them in chronological order (oldest first)
    for fb_post in reversed(new_posts):
        post_id = fb_post.get("id")
        print(f"Publishing Facebook post ID to Threads: {post_id}")
        success = post_to_threads(fb_post, threads_token)
        if success:
            state["last_fb_post_id"] = post_id
            # Save state after each successful post to prevent duplicate posting if a later post fails
            save_state(state)
            # Sleep briefly between posts if there are multiple
            if len(new_posts) > 1:
                time.sleep(10)
        else:
            print(f"Failed to publish post {post_id}. Stopping execution to avoid skipping.")
            break

if __name__ == "__main__":
    main()
