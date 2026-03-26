import streamlit as st
import os
import time
import tempfile
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from gtts import gTTS
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip
import requests
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="AI Stock Video Creator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== INITIALIZE SESSION STATE ====================
if 'youtube_connected' not in st.session_state:
    st.session_state.youtube_connected = False
if 'youtube_credentials' not in st.session_state:
    st.session_state.youtube_credentials = None
if 'video_path' not in st.session_state:
    st.session_state.video_path = None
if 'generated_videos' not in st.session_state:
    st.session_state.generated_videos = []

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #00ff88, #00cc66);
        color: black;
        font-weight: bold;
        font-size: 18px;
        border-radius: 10px;
        padding: 10px;
    }
    .stock-card {
        padding: 20px;
        border-radius: 10px;
        background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
        margin: 10px 0;
        border-left: 4px solid #00ff88;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #00ff88;
    }
    .youtube-connected {
        background-color: #00ff8822;
        border: 1px solid #00ff88;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==================== TITLE ====================
st.title("📈 AI-Powered Stock Video Creator")
st.caption("Generate stock videos with AI voiceover | Auto-post to YouTube")

# ==================== SIDEBAR - YOUTUBE AUTHENTICATION ====================
with st.sidebar:
    st.header("🔑 YouTube Authentication")
    
    # Option 1: File upload method (Easiest)
    st.subheader("Method 1: Upload OAuth File")
    uploaded_file = st.file_uploader(
        "Upload client_secrets.json",
        type=['json'],
        help="Download from Google Cloud Console (Desktop app type)"
    )
    
    if uploaded_file:
        # Save uploaded file to temporary location
        secrets_path = tempfile.mktemp(suffix=".json")
        with open(secrets_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        st.success("✅ Credentials file loaded!")
        
        # Connect YouTube button
        if st.button("🔌 Connect to YouTube", key="connect_youtube_btn"):
            with st.spinner("Connecting to YouTube..."):
                try:
                    # OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        secrets_path,
                        scopes=['https://www.googleapis.com/auth/youtube.upload']
                    )
                    
                    # This opens a browser window for authentication
                    credentials = flow.run_local_server(port=8080)
                    
                    # Save credentials to session
                    st.session_state.youtube_credentials = credentials
                    st.session_state.youtube_connected = True
                    
                    # Also save to file for future runs
                    with open('youtube_token.pickle', 'wb') as token_file:
                        pickle.dump(credentials, token_file)
                    
                    st.success("✅ YouTube connected successfully!")
                    
                    # Clean up temp file
                    os.remove(secrets_path)
                    
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
                    st.info("Make sure you've downloaded the correct client_secrets.json file")
    
    # Option 2: Use saved token (if available)
    st.subheader("Method 2: Use Saved Token")
    if os.path.exists('youtube_token.pickle'):
        if st.button("🔌 Connect with Saved Token"):
            try:
                with open('youtube_token.pickle', 'rb') as token_file:
                    credentials = pickle.load(token_file)
                
                # Check if token is expired
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    with open('youtube_token.pickle', 'wb') as token_file:
                        pickle.dump(credentials, token_file)
                
                st.session_state.youtube_credentials = credentials
                st.session_state.youtube_connected = True
                st.success("✅ Connected with saved token!")
                
            except Exception as e:
                st.error(f"Failed to load token: {str(e)}")
    else:
        st.info("No saved token found. Use Method 1 first.")
    
    # Display connection status
    st.divider()
    if st.session_state.youtube_connected:
        st.markdown("""
        <div class="youtube-connected">
        ✅ <strong>YouTube Connected!</strong><br>
        Ready to upload videos
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="youtube-connected" style="background-color: #ff000022; border-color: #ff4444;">
        ❌ <strong>YouTube Not Connected</strong><br>
        Upload client_secrets.json to connect
        </div>
        """, unsafe_allow_html=True)
    
    # Stock selection
    st.divider()
    st.header("📊 Stock Selection")
    STOCKS = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "AMD"]
    selected_stocks = st.multiselect("Select stocks", STOCKS, default=STOCKS[:4])

# ==================== MAIN CONTENT AREA ====================
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🎬 Generate Stock Video")
    
    # Manual generation
    manual_symbol = st.selectbox("Select stock to generate video", ["Select a stock"] + STOCKS)
    
    col_orient1, col_orient2 = st.columns(2)
    with col_orient1:
        orientation = st.radio("Video Orientation", ["Horizontal (YouTube)", "Vertical (Shorts)"], index=0)
    
    # Generate video button
    if st.button("🚀 Generate Video", type="primary", use_container_width=True):
        if manual_symbol != "Select a stock":
            with st.spinner(f"Generating video for {manual_symbol}..."):
                try:
                    video_path = generate_stock_video(
                        manual_symbol, 
                        "vertical" if "Vertical" in orientation else "horizontal"
                    )
                    if video_path:
                        st.session_state.video_path = video_path
                        st.session_state.generated_videos.append(video_path)
                        st.success(f"✅ Video generated for {manual_symbol}!")
                        st.video(video_path)
                        
                        # Download button
                        with open(video_path, 'rb') as f:
                            st.download_button(
                                label="📥 Download Video",
                                data=f,
                                file_name=f"{manual_symbol}_video.mp4",
                                mime="video/mp4"
                            )
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please select a stock")
    
    # Upload to YouTube section
    if st.session_state.video_path:
        st.divider()
        st.header("📤 Upload to YouTube")
        
        # Video metadata
        title = st.text_input("Video Title", f"Stock Market Update - {datetime.now().strftime('%Y-%m-%d')}")
        description = st.text_area("Description", "AI-generated stock market analysis. Not financial advice. #Stocks #Trading #AI")
        tags = st.text_input("Tags (comma separated)", "stocks, trading, AI, finance, market analysis")
        
        col_upload1, col_upload2 = st.columns(2)
        with col_upload1:
            if st.button("📺 Upload to YouTube", use_container_width=True):
                if st.session_state.youtube_connected:
                    with st.spinner("Uploading to YouTube..."):
                        success = upload_to_youtube(
                            st.session_state.video_path,
                            title,
                            description,
                            [tag.strip() for tag in tags.split(',')]
                        )
                        if success:
                            st.balloons()
                            st.success("🎉 Video uploaded to YouTube successfully!")
                else:
                    st.error("Please connect YouTube account first (see sidebar)")
        
        with col_upload2:
            if st.button("📱 Post to YouTube Shorts", use_container_width=True):
                if st.session_state.youtube_connected:
                    with st.spinner("Uploading to YouTube Shorts..."):
                        shorts_title = f"{title} #Shorts"
                        success = upload_to_youtube(
                            st.session_state.video_path,
                            shorts_title,
                            description,
                            [tag.strip() for tag in tags.split(',')] + ["shorts"],
                            is_shorts=True
                        )
                        if success:
                            st.success("🎉 Video uploaded as YouTube Shorts!")
                else:
                    st.error("Please connect YouTube account first")

with col2:
    st.header("📊 Live Stock Dashboard")
    
    # Display real-time stock data
    for symbol in selected_stocks:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            change = info.get('regularMarketChangePercent', 0)
            
            st.markdown(f"""
            <div class="stock-card">
                <h3>{symbol}</h3>
                <div class="metric-value">${price:.2f}</div>
                <div style="color: {'#00ff88' if change >= 0 else '#ff4444'}">
                    {change:+.2f}%
                </div>
                <small>Last updated: {datetime.now().strftime('%H:%M:%S')}</small>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading {symbol}: {str(e)}")
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.rerun()

# ==================== FUNCTIONS ====================

def get_stock_data(symbol):
    """Fetch current stock data"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1d")
        
        price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        prev_close = info.get('regularMarketPreviousClose', price)
        change = ((price - prev_close) / prev_close * 100) if prev_close else 0
        
        return {
            'symbol': symbol,
            'price': price,
            'change': change,
            'volume': info.get('volume', 0),
            'high': info.get('dayHigh', price),
            'low': info.get('dayLow', price)
        }
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
        return None

def get_prediction(info):
    """Simple prediction based on price action"""
    change = info['change']
    
    if change > 1.5:
        signal = "BULLISH"
        reason = "strong upward momentum detected"
    elif change > 0.5:
        signal = "SLIGHTLY BULLISH"
        reason = "positive price action"
    elif change > -0.5:
        signal = "NEUTRAL"
        reason = "consolidation phase"
    elif change > -1.5:
        signal = "SLIGHTLY BEARISH"
        reason = "minor selling pressure"
    else:
        signal = "BEARISH"
        reason = "significant downward movement"
    
    return {
        'signal': signal,
        'reason': reason,
        'confidence': min(abs(change) * 20, 95)
    }

def generate_stock_video(symbol, orientation="horizontal"):
    """Generate stock video with chart and AI voiceover"""
    
    # Get data
    info = get_stock_data(symbol)
    if not info:
        return None
    
    pred = get_prediction(info)
    
    # Set dimensions based on orientation
    if orientation == "vertical":
        size = (1080, 1920)
        title = f"🚨 {symbol} AI ALERT"
        font_size = 90
    else:
        size = (1920, 1080)
        title = f"{symbol} Live • AI Prediction"
        font_size = 120
    
    # Create stock chart
    data = yf.download(symbol, period="1d", interval="5m")
    if data.empty:
        # Create mock data if real data unavailable
        dates = pd.date_range(start=datetime.now() - timedelta(hours=6), periods=72, freq='5min')
        data = pd.DataFrame({'Close': np.random.normal(info['price'], info['price']*0.01, 72)}, index=dates)
    
    # Plot chart
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    
    ax.plot(data.index, data['Close'], label="Price", color="#00ff88", linewidth=4)
    ax.fill_between(data.index, data['Close'].min(), data['Close'], alpha=0.3, color="#00ff88")
    ax.set_title(f"{symbol} ${info['price']:.2f} | {pred['signal']}", fontsize=font_size/2, color="white", pad=20)
    ax.set_xlabel("Time", fontsize=font_size/3, color="white")
    ax.set_ylabel("Price ($)", fontsize=font_size/3, color="white")
    ax.legend(fontsize=font_size/3)
    ax.grid(alpha=0.3)
    ax.set_facecolor("#111111")
    
    # Save chart
    chart_path = tempfile.mktemp(suffix=".png")
    plt.savefig(chart_path, bbox_inches='tight', facecolor="#111111")
    plt.close()
    
    # Generate AI voiceover
    text = f"{symbol} is now at ${info['price']:.2f}. That's {info['change']:+.2f} percent. Our AI predicts {pred['signal']}. Reason: {pred['reason']}. Confidence level {pred['confidence']:.0f} percent. This is not financial advice. Always do your own research."
    
    tts = gTTS(text, lang='en', slow=False)
    audio_path = tempfile.mktemp(suffix=".mp3")
    tts.save(audio_path)
    
    # Create video
    try:
        # Image clip
        img_clip = ImageClip(chart_path).set_duration(15).resize(size)
        
        # Text clip
        txt_clip = TextClip(
            title, 
            fontsize=font_size, 
            color='#00ff88', 
            font='Arial-Bold',
            stroke_color='black',
            stroke_width=2
        ).set_position('center').set_duration(15)
        
        # Combine
        video = CompositeVideoClip([img_clip, txt_clip])
        
        # Add audio
        audio_clip = AudioFileClip(audio_path)
        video = video.set_audio(audio_clip)
        
        # Export
        video_path = tempfile.mktemp(suffix=".mp4")
        video.write_videofile(
            video_path, 
            fps=24, 
            codec='libx264', 
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        # Cleanup temp files
        try:
            os.remove(chart_path)
            os.remove(audio_path)
        except:
            pass
        
        return video_path
        
    except Exception as e:
        st.error(f"Video creation error: {str(e)}")
        return None

def upload_to_youtube(video_path, title, description, tags, is_shorts=False):
    """Upload video to YouTube"""
    if not st.session_state.youtube_connected:
        st.error("YouTube not connected")
        return False
    
    try:
        credentials = st.session_state.youtube_credentials
        
        # Build YouTube service
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # Video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }
        
        # For Shorts, add #Shorts to title if not already there
        if is_shorts and "#Shorts" not in title:
            body['snippet']['title'] = f"{title} #Shorts"
        
        # Upload video
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True
        )
        
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = request.execute()
        video_id = response['id']
        
        st.success(f"✅ Uploaded to YouTube! Video ID: {video_id}")
        st.markdown(f"[Watch on YouTube](https://youtu.be/{video_id})")
        
        return True
        
    except Exception as e:
        st.error(f"YouTube upload failed: {str(e)}")
        return False

# ==================== FOOTER ====================
st.divider()
st.caption("🤖 AI-Powered Stock Video Creator | Real-time data | AI predictions | YouTube Auto-upload")
st.caption("⚠️ Not financial advice. Always do your own research before investing.")
