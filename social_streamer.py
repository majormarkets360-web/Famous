import os
import time
import json
import base64
import tempfile
from datetime import datetime
import requests
from io import BytesIO

# Optional imports with fallbacks
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

import pickle

class SocialMediaStreamer:
    """Unified social media streaming handler"""
    
    def __init__(self):
        self.connected_platforms = {}
        
    def connect_twitter(self, api_key, api_secret, access_token, access_secret):
        """Connect to Twitter/X"""
        if not TWEEPY_AVAILABLE:
            return False, "Tweepy not installed. Run: pip install tweepy"
        
        try:
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            api = tweepy.API(auth)
            # Test connection
            api.verify_credentials()
            self.connected_platforms['twitter'] = api
            return True, "Twitter connected successfully!"
        except Exception as e:
            return False, f"Twitter connection failed: {str(e)}"
    
    def connect_youtube(self, client_secrets_file):
        """Connect to YouTube"""
        if not GOOGLE_AVAILABLE:
            return False, "Google libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client"
        
        try:
            credentials = None
            token_file = 'youtube_token.pickle'
            
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    credentials = pickle.load(token)
            
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secrets_file,
                        scopes=['https://www.googleapis.com/auth/youtube.upload']
                    )
                    credentials = flow.run_local_server(port=8080)
                
                with open(token_file, 'wb') as token:
                    pickle.dump(credentials, token)
            
            youtube = build('youtube', 'v3', credentials=credentials)
            self.connected_platforms['youtube'] = youtube
            return True, "YouTube connected successfully!"
        except Exception as e:
            return False, f"YouTube connection failed: {str(e)}"
    
    def connect_facebook(self, access_token, page_id=None):
        """Connect to Facebook"""
        try:
            self.connected_platforms['facebook'] = {
                'token': access_token,
                'page_id': page_id
            }
            # Test connection
            url = f"https://graph.facebook.com/me?access_token={access_token}"
            response = requests.get(url)
            if response.status_code == 200:
                return True, "Facebook connected successfully!"
            else:
                return False, "Invalid Facebook token"
        except Exception as e:
            return False, f"Facebook connection failed: {str(e)}"
    
    def connect_tiktok(self, session_id=None, access_token=None):
        """Connect to TikTok (via session cookie or API)"""
        try:
            # TikTok API connection (simplified - you'll need to implement full OAuth)
            self.connected_platforms['tiktok'] = {
                'session_id': session_id,
                'access_token': access_token
            }
            return True, "TikTok configured (full OAuth required for production)"
        except Exception as e:
            return False, f"TikTok connection failed: {str(e)}"
    
    def create_video_from_data(self, stock_data, chart_image, audio_voiceover=None):
        """Create a short video from stock data for social media"""
        if not MOVIEPY_AVAILABLE:
            return None
        
        try:
            # Create video with stock data overlay
            video_path = tempfile.mktemp(suffix=".mp4")
            
            # Image clip from chart
            img_clip = ImageClip(chart_image).set_duration(15).resize((1080, 1920))
            
            # Add text overlays
            txt_clip = TextClip(
                f"{stock_data['symbol']}: ${stock_data['price']:.2f}\n{stock_data['action']} Signal - {stock_data['confidence']}%",
                fontsize=40,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2
            ).set_position(('center', 'top')).set_duration(15)
            
            # Combine
            video = CompositeVideoClip([img_clip, txt_clip])
            
            # Add audio if provided
            if audio_voiceover:
                audio_clip = AudioFileClip(audio_voiceover)
                video = video.set_audio(audio_clip)
            
            # Write video
            video.write_videofile(video_path, fps=24, codec='libx264', audio_codec='aac', verbose=False, logger=None)
            
            return video_path
        except Exception as e:
            return None
    
    def post_to_twitter(self, message, image_path=None, video_path=None):
        """Post to Twitter/X"""
        if 'twitter' not in self.connected_platforms:
            return False, "Twitter not connected"
        
        try:
            api = self.connected_platforms['twitter']
            
            if video_path:
                # Upload video (Twitter requires specific format)
                media = api.media_upload(video_path, media_category="tweet_video")
                api.update_status(status=message[:280], media_ids=[media.media_id])
                return True, "Video posted to Twitter!"
            
            elif image_path:
                media = api.media_upload(image_path)
                api.update_status(status=message[:280], media_ids=[media.media_id])
                return True, "Image posted to Twitter!"
            
            else:
                api.update_status(status=message[:280])
                return True, "Tweet posted!"
                
        except Exception as e:
            return False, f"Twitter post failed: {str(e)}"
    
    def post_to_youtube(self, video_path, title, description, tags, is_shorts=False):
        """Post to YouTube/YouTube Shorts"""
        if 'youtube' not in self.connected_platforms:
            return False, "YouTube not connected"
        
        if not GOOGLE_AVAILABLE:
            return False, "Google libraries not available"
        
        try:
            youtube = self.connected_platforms['youtube']
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22'
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
            
            return True, f"YouTube video posted! ID: {response['id']}"
            
        except Exception as e:
            return False, f"YouTube post failed: {str(e)}"
    
    def post_to_facebook(self, message, video_path=None, image_path=None):
        """Post to Facebook/Instagram"""
        if 'facebook' not in self.connected_platforms:
            return False, "Facebook not connected"
        
        try:
            fb_data = self.connected_platforms['facebook']
            access_token = fb_data['token']
            page_id = fb_data.get('page_id', 'me')
            
            if video_path:
                # Upload video to Facebook
                url = f"https://graph.facebook.com/{page_id}/videos"
                with open(video_path, 'rb') as f:
                    files = {'source': f}
                    params = {
                        'access_token': access_token,
                        'description': message
                    }
                    response = requests.post(url, files=files, params=params)
                
                if response.status_code == 200:
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
                        'caption': message
                    }
                    response = requests.post(url, files=files, params=params)
                
                if response.status_code == 200:
                    return True, "Image posted to Facebook!"
                else:
                    return False, f"Facebook photo upload failed: {response.text}"
            
            else:
                # Post text update
                url = f"https://graph.facebook.com/{page_id}/feed"
                params = {
                    'access_token': access_token,
                    'message': message
                }
                response = requests.post(url, params=params)
                
                if response.status_code == 200:
                    return True, "Post published to Facebook!"
                else:
                    return False, f"Facebook post failed: {response.text}"
                    
        except Exception as e:
            return False, f"Facebook post failed: {str(e)}"
    
    def post_to_tiktok(self, video_path, title, hashtags):
        """Post to TikTok"""
        if 'tiktok' not in self.connected_platforms:
            return False, "TikTok not configured"
        
        try:
            # TikTok requires full OAuth flow - this is a placeholder
            # You'll need to implement the full TikTok API OAuth flow
            tiktok_data = self.connected_platforms['tiktok']
            
            # Placeholder for TikTok API integration
            return True, "TikTok post ready (full OAuth required for production)"
            
        except Exception as e:
            return False, f"TikTok post failed: {str(e)}"
    
    def stream_to_all(self, data, message, video_path=None, image_path=None):
        """Post to all connected platforms simultaneously"""
        results = {}
        
        # Post to Twitter
        if 'twitter' in self.connected_platforms:
            success, msg = self.post_to_twitter(message, image_path, video_path)
            results['twitter'] = {'success': success, 'message': msg}
        
        # Post to YouTube
        if 'youtube' in self.connected_platforms and video_path:
            success, msg = self.post_to_youtube(
                video_path,
                f"AI Trading Alert: {data.get('symbol', 'Market Update')}",
                message,
                ['stocks', 'trading', 'ai', 'market'],
                is_shorts=True
            )
            results['youtube'] = {'success': success, 'message': msg}
        
        # Post to Facebook
        if 'facebook' in self.connected_platforms:
            success, msg = self.post_to_facebook(message, video_path, image_path)
            results['facebook'] = {'success': success, 'message': msg}
        
        # Post to TikTok
        if 'tiktok' in self.connected_platforms and video_path:
            success, msg = self.post_to_tiktok(video_path, data.get('symbol', 'Market'), '#stocks #trading #ai')
            results['tiktok'] = {'success': success, 'message': msg}
        
        return results
