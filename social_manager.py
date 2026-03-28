import streamlit as st
import os
import time
import json
import requests
import base64
from datetime import datetime
import tempfile
from PIL import Image
import io

# Twitter/X API
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

# YouTube API
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

class SocialMediaManager:
    """Unified social media manager for auto-posting and streaming"""
    
    def __init__(self):
        self.connected_platforms = {}
        self.post_history = []
        
    # ==================== TWITTER/X CONNECTION ====================
    def connect_twitter(self, api_key, api_secret, access_token, access_secret):
        """Connect to Twitter/X"""
        if not TWEEPY_AVAILABLE:
            return False, "Tweepy not installed. Run: pip install tweepy"
        
        try:
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            api = tweepy.API(auth)
            # Test connection
            api.verify_credentials()
            self.connected_platforms['twitter'] = {
                'api': api,
                'api_key': api_key,
                'api_secret': api_secret,
                'access_token': access_token,
                'access_secret': access_secret
            }
            return True, "Twitter connected successfully!"
        except Exception as e:
            return False, f"Twitter connection failed: {str(e)}"
    
    def post_to_twitter(self, message, image_path=None, video_path=None):
        """Post to Twitter/X"""
        if 'twitter' not in self.connected_platforms:
            return False, "Twitter not connected"
        
        try:
            api = self.connected_platforms['twitter']['api']
            
            # Truncate message to Twitter's limit
            if len(message) > 280:
                message = message[:277] + "..."
            
            if video_path:
                # Upload video (Twitter requires specific format)
                media = api.media_upload(video_path, media_category="tweet_video")
                api.update_status(status=message, media_ids=[media.media_id])
                self._log_post('twitter', message, video_path)
                return True, "Video posted to Twitter!"
            
            elif image_path:
                media = api.media_upload(image_path)
                api.update_status(status=message, media_ids=[media.media_id])
                self._log_post('twitter', message, image_path)
                return True, "Image posted to Twitter!"
            
            else:
                api.update_status(status=message)
                self._log_post('twitter', message)
                return True, "Tweet posted!"
                
        except Exception as e:
            return False, f"Twitter post failed: {str(e)}"
    
    # ==================== YOUTUBE CONNECTION ====================
    def connect_youtube(self, client_secrets_file):
        """Connect to YouTube using OAuth"""
        if not YOUTUBE_AVAILABLE:
            return False, "Google libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client"
        
        try:
            credentials = None
            token_file = 'youtube_token.pickle'
            
            # Check for saved credentials
            import pickle
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    credentials = pickle.load(token)
            
            # If no valid credentials, get new ones
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secrets_file,
                        scopes=['https://www.googleapis.com/auth/youtube.upload']
                    )
                    # Use manual code flow for headless environments
                    credentials = flow.run_local_server(port=8080)
                
                # Save credentials
                with open(token_file, 'wb') as token:
                    pickle.dump(credentials, token)
            
            youtube = build('youtube', 'v3', credentials=credentials)
            self.connected_platforms['youtube'] = {
                'youtube': youtube,
                'credentials': credentials
            }
            return True, "YouTube connected successfully!"
            
        except Exception as e:
            return False, f"YouTube connection failed: {str(e)}"
    
    def post_to_youtube(self, video_path, title, description, tags, is_shorts=False):
        """Post to YouTube/YouTube Shorts"""
        if 'youtube' not in self.connected_platforms:
            return False, "YouTube not connected"
        
        try:
            youtube = self.connected_platforms['youtube']['youtube']
            
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description[:5000],
                    'tags': tags[:500],
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }
            
            if is_shorts and "#Shorts" not in title:
                body['snippet']['title'] = f"{title} #Shorts"
            
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            response = request.execute()
            
            video_id = response['id']
            self._log_post('youtube', title, video_path, video_id)
            return True, f"YouTube video posted! ID: {video_id}"
            
        except Exception as e:
            return False, f"YouTube post failed: {str(e)}"
    
    # ==================== FACEBOOK CONNECTION ====================
    def connect_facebook(self, access_token, page_id=None):
        """Connect to Facebook/Instagram"""
        try:
            # Test the token
            url = f"https://graph.facebook.com/me?access_token={access_token}"
            response = requests.get(url)
            
            if response.status_code == 200:
                self.connected_platforms['facebook'] = {
                    'token': access_token,
                    'page_id': page_id or 'me'
                }
                return True, "Facebook connected successfully!"
            else:
                return False, "Invalid Facebook token"
                
        except Exception as e:
            return False, f"Facebook connection failed: {str(e)}"
    
    def post_to_facebook(self, message, video_path=None, image_path=None):
        """Post to Facebook/Instagram"""
        if 'facebook' not in self.connected_platforms:
            return False, "Facebook not connected"
        
        try:
            fb_data = self.connected_platforms['facebook']
            access_token = fb_data['token']
            page_id = fb_data['page_id']
            
            if video_path:
                # Upload video to Facebook
                url = f"https://graph.facebook.com/{page_id}/videos"
                with open(video_path, 'rb') as f:
                    files = {'source': f}
                    params = {
                        'access_token': access_token,
                        'description': message[:1000]
                    }
                    response = requests.post(url, files=files, params=params)
                
                if response.status_code == 200:
                    self._log_post('facebook', message, video_path)
                    return True, "Video posted to Facebook!"
                else:
                    return False, f"Facebook video upload failed: {response.text}"
            
            elif image_path:
                # Upload photo to Facebook
                url = f"https://graph.facebook.com/{page_id}/photos"
                with open(image_path, 'rb') as f:
                    files = {'source': f}
                    params = {
                        'access_token': access_token,
                        'caption': message[:1000]
                    }
                    response = requests.post(url, files=files, params=params)
                
                if response.status_code == 200:
                    self._log_post('facebook', message, image_path)
                    return True, "Image posted to Facebook!"
                else:
                    return False, f"Facebook photo upload failed: {response.text}"
            
            else:
                # Post text update
                url = f"https://graph.facebook.com/{page_id}/feed"
                params = {
                    'access_token': access_token,
                    'message': message[:1000]
                }
                response = requests.post(url, params=params)
                
                if response.status_code == 200:
                    self._log_post('facebook', message)
                    return True, "Post published to Facebook!"
                else:
                    return False, f"Facebook post failed: {response.text}"
                    
        except Exception as e:
            return False, f"Facebook post failed: {str(e)}"
    
    # ==================== INSTAGRAM CONNECTION ====================
    def connect_instagram(self, access_token, business_account_id):
        """Connect to Instagram Business Account"""
        try:
            # Test the connection
            url = f"https://graph.facebook.com/v12.0/{business_account_id}?fields=id,username&access_token={access_token}"
            response = requests.get(url)
            
            if response.status_code == 200:
                self.connected_platforms['instagram'] = {
                    'token': access_token,
                    'account_id': business_account_id
                }
                return True, "Instagram connected successfully!"
            else:
                return False, "Invalid Instagram credentials"
                
        except Exception as e:
            return False, f"Instagram connection failed: {str(e)}"
    
    def post_to_instagram(self, caption, image_path=None, video_path=None):
        """Post to Instagram (Business Account Required)"""
        if 'instagram' not in self.connected_platforms:
            return False, "Instagram not connected"
        
        try:
            ig_data = self.connected_platforms['instagram']
            access_token = ig_data['token']
            account_id = ig_data['account_id']
            
            if image_path:
                # Step 1: Create media container
                url = f"https://graph.facebook.com/v12.0/{account_id}/media"
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                params = {
                    'access_token': access_token,
                    'image_url': f"data:image/jpeg;base64,{image_data}",
                    'caption': caption[:2200]
                }
                response = requests.post(url, params=params)
                
                if response.status_code == 200:
                    creation_id = response.json().get('id')
                    
                    # Step 2: Publish the container
                    publish_url = f"https://graph.facebook.com/v12.0/{account_id}/media_publish"
                    publish_params = {
                        'access_token': access_token,
                        'creation_id': creation_id
                    }
                    publish_response = requests.post(publish_url, params=publish_params)
                    
                    if publish_response.status_code == 200:
                        self._log_post('instagram', caption, image_path)
                        return True, "Image posted to Instagram!"
                
                return False, "Instagram post failed"
            
            elif video_path:
                # Instagram Reels/Video posting
                url = f"https://graph.facebook.com/v12.0/{account_id}/media"
                params = {
                    'access_token': access_token,
                    'media_type': 'VIDEO',
                    'video_url': f"file://{video_path}",
                    'caption': caption[:2200]
                }
                response = requests.post(url, params=params)
                
                if response.status_code == 200:
                    creation_id = response.json().get('id')
                    
                    # Publish
                    publish_url = f"https://graph.facebook.com/v12.0/{account_id}/media_publish"
                    publish_params = {
                        'access_token': access_token,
                        'creation_id': creation_id
                    }
                    publish_response = requests.post(publish_url, params=publish_params)
                    
                    if publish_response.status_code == 200:
                        self._log_post('instagram', caption, video_path)
                        return True, "Video posted to Instagram!"
                
                return False, "Instagram video post failed"
            
            else:
                return False, "No media provided for Instagram post"
                
        except Exception as e:
            return False, f"Instagram post failed: {str(e)}"
    
    # ==================== TIKTOK CONNECTION ====================
    def connect_tiktok(self, access_token=None, session_id=None):
        """Connect to TikTok"""
        try:
            self.connected_platforms['tiktok'] = {
                'access_token': access_token,
                'session_id': session_id
            }
            return True, "TikTok configured (full OAuth required for production)"
        except Exception as e:
            return False, f"TikTok connection failed: {str(e)}"
    
    def post_to_tiktok(self, video_path, title, hashtags):
        """Post to TikTok"""
        if 'tiktok' not in self.connected_platforms:
            return False, "TikTok not configured"
        
        try:
            # TikTok requires full OAuth flow
            # This is a placeholder for the TikTok API integration
            # You'll need to implement the full TikTok API OAuth flow
            self._log_post('tiktok', title, video_path)
            return True, "TikTok post ready (full OAuth required for production)"
            
        except Exception as e:
            return False, f"TikTok post failed: {str(e)}"
    
    # ==================== POST TO ALL PLATFORMS ====================
    def post_to_all(self, message, video_path=None, image_path=None, title=None, tags=None):
        """Post to all connected platforms simultaneously"""
        results = {}
        
        # Post to Twitter
        if 'twitter' in self.connected_platforms:
            success, msg = self.post_to_twitter(message, image_path, video_path)
            results['twitter'] = {'success': success, 'message': msg}
        
        # Post to Facebook
        if 'facebook' in self.connected_platforms:
            success, msg = self.post_to_facebook(message, video_path, image_path)
            results['facebook'] = {'success': success, 'message': msg}
        
        # Post to Instagram
        if 'instagram' in self.connected_platforms and (image_path or video_path):
            success, msg = self.post_to_instagram(message, image_path, video_path)
            results['instagram'] = {'success': success, 'message': msg}
        
        # Post to YouTube
        if 'youtube' in self.connected_platforms and video_path:
            success, msg = self.post_to_youtube(
                video_path,
                title or "Market Update",
                message,
                tags or ['stocks', 'trading', 'ai'],
                is_shorts=True
            )
            results['youtube'] = {'success': success, 'message': msg}
        
        # Post to TikTok
        if 'tiktok' in self.connected_platforms and video_path:
            success, msg = self.post_to_tiktok(video_path, title or "Market Update", '#stocks #trading')
            results['tiktok'] = {'success': success, 'message': msg}
        
        return results
    
    # ==================== AUTO-STREAM SETUP ====================
    def start_auto_stream(self, interval_minutes=15):
        """Start automatic streaming to all platforms"""
        import threading
        import schedule
        
        def auto_stream_job():
            """Job to run auto-streaming"""
            # Get latest market data
            message = generate_market_update()
            
            # Post to all platforms
            results = self.post_to_all(message)
            
            # Log results
            for platform, result in results.items():
                if result['success']:
                    print(f"Auto-stream: Posted to {platform}")
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(auto_stream_job)
        
        # Run in background thread
        def run_schedule():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        thread = threading.Thread(target=run_schedule, daemon=True)
        thread.start()
        
        return True, f"Auto-stream started (every {interval_minutes} minutes)"
    
    # ==================== HELPER FUNCTIONS ====================
    def _log_post(self, platform, content, media_path=None, media_id=None):
        """Log posted content"""
        self.post_history.append({
            'platform': platform,
            'content': content[:100],
            'media': media_path,
            'media_id': media_id,
            'timestamp': datetime.now()
        })
        # Keep only last 100 posts
        self.post_history = self.post_history[-100:]
    
    def get_post_history(self):
        """Get posting history"""
        return self.post_history
    
    def get_connected_platforms(self):
        """Get list of connected platforms"""
        return list(self.connected_platforms.keys())
    
    def disconnect_all(self):
        """Disconnect all platforms"""
        self.connected_platforms = {}
        return True, "All platforms disconnected"

def generate_market_update():
    """Generate a market update message for auto-posting"""
    try:
        import yfinance as yf
        spy = yf.Ticker("SPY")
        info = spy.info
        price = info.get('regularMarketPrice', 0)
        change = info.get('regularMarketChangePercent', 0)
        
        sentiment = "🟢 BULLISH" if change > 0 else "🔴 BEARISH"
        
        return f"""🤖 AI Market Update

S&P 500: ${price:.2f} ({change:+.2f}%)
Market Sentiment: {sentiment}

AI Prediction: {'Positive momentum expected' if change > 0 else 'Caution advised'}

#Stocks #Trading #AI #MarketAnalysis"""
    except:
        return "🤖 AI Market Update - Check the dashboard for latest insights!"
