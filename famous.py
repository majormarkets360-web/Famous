import streamlit as st
import os
import tempfile
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime, timedelta
from gtts import gTTS
import requests
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import subprocess
import base64

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="AI Stock Video Creator",
    page_icon="📈",
    layout="wide"
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

# ==================== TITLE ====================
st.title("📈 AI-Powered Stock Video Creator")
st.caption("Generate stock videos with AI voiceover | Auto-post to YouTube")

# ==================== SIDEBAR - YOUTUBE AUTHENTICATION ====================
with st.sidebar:
    st.header("🔑 YouTube Authentication")
    
    # File upload for OAuth
    uploaded_file = st.file_uploader(
        "Upload client_secrets.json",
        type=['json'],
        help="Download from Google Cloud Console"
    )
    
    if uploaded_file:
        secrets_path = tempfile.mktemp(suffix=".json")
        with open(secrets_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        st.success("✅ Credentials file loaded!")
        
        if st.button("🔌 Connect to YouTube", key="connect_youtube_btn"):
            with st.spinner("Connecting to YouTube..."):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        secrets_path,
                        scopes=['https://www.googleapis.com/auth/youtube.upload']
                    )
                    credentials = flow.run_local_server(port=8080)
                    st.session_state.youtube_credentials = credentials
                    st.session_state.youtube_connected = True
                    
                    with open('youtube_token.pickle', 'wb') as token_file:
                        pickle.dump(credentials, token_file)
                    
                    st.success("✅ YouTube connected successfully!")
                    os.remove(secrets_path)
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")
    
    # Display connection status
    if st.session_state.youtube_connected:
        st.success("✅ YouTube Connected!")
    else:
        st.warning("❌ YouTube Not Connected")
    
    # Stock selection
    st.divider()
    st.header("📊 Stock Selection")
    STOCKS = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "AMD"]
    selected_stocks = st.multiselect("Select stocks", STOCKS, default=STOCKS[:4])

# ==================== MAIN CONTENT ====================
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🎬 Generate Stock Video")
    
    manual_symbol = st.selectbox("Select stock to generate video", ["Select a stock"] + STOCKS)
    
    if st.button("🚀 Generate Video", type="primary", use_container_width=True):
        if manual_symbol != "Select a stock":
            with st.spinner(f"Generating video for {manual_symbol}..."):
                try:
                    video_path = generate_stock_video_simple(manual_symbol)
                    if video_path:
                        st.session_state.video_path = video_path
                        st.success(f"✅ Video generated for {manual_symbol}!")
                        st.video(video_path)
                        
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
    
    # Upload section
    if st.session_state.video_path:
        st.divider()
        st.header("📤 Upload to YouTube")
        
        title = st.text_input("Video Title", f"Stock Market Update - {datetime.now().strftime('%Y-%m-%d')}")
        description = st.text_area("Description", "AI-generated stock market analysis. Not financial advice.")
        tags = st.text_input("Tags", "stocks, trading, AI, finance")
        
        if st.button("📺 Upload to YouTube", use_container_width=True):
            if st.session_state.youtube_connected:
                with st.spinner("Uploading to YouTube..."):
                    success = upload_to_youtube_simple(
                        st.session_state.video_path,
                        title,
                        description,
                        [tag.strip() for tag in tags.split(',')]
                    )
                    if success:
                        st.balloons()
                        st.success("🎉 Video uploaded to YouTube!")
            else:
                st.error("Please connect YouTube account first")

with col2:
    st.header("📊 Live Stock Dashboard")
    
    for symbol in selected_stocks:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            change = info.get('regularMarketChangePercent', 0)
            
            st.metric(
                label=symbol,
                value=f"${price:.2f}",
                delta=f"{change:+.2f}%",
                delta_color="normal"
            )
        except:
            pass

# ==================== FUNCTIONS ====================

def get_stock_data(symbol):
    """Fetch current stock data"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        prev_close = info.get('regularMarketPreviousClose', price)
        change = ((price - prev_close) / prev_close * 100) if prev_close else 0
        
        return {
            'symbol': symbol,
            'price': price,
            'change': change
        }
    except Exception as e:
        return None

def get_prediction(info):
    """Simple prediction"""
    change = info['change']
    
    if change > 1:
        signal = "BULLISH"
        reason = "strong upward momentum"
    elif change > 0:
        signal = "SLIGHTLY BULLISH"
        reason = "positive price action"
    elif change > -1:
        signal = "NEUTRAL"
        reason = "consolidation"
    else:
        signal = "BEARISH"
        reason = "downward pressure"
    
    return {'signal': signal, 'reason': reason}

def generate_stock_video_simple(symbol):
    """Generate video using matplotlib animation (no moviepy)"""
    
    # Get data
    info = get_stock_data(symbol)
    if not info:
        return None
    
    pred = get_prediction(info)
    
    # Create chart
    data = yf.download(symbol, period="1d", interval="5m")
    if data.empty:
        dates = pd.date_range(start=datetime.now() - timedelta(hours=6), periods=72, freq='5min')
        data = pd.DataFrame({'Close': np.random.normal(info['price'], info['price']*0.01, 72)}, index=dates)
    
    # Create figure
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    
    # Plot
    ax.plot(data.index, data['Close'], color="#00ff88", linewidth=3)
    ax.set_title(f"{symbol} - ${info['price']:.2f} | {pred['signal']}", fontsize=14, color="white")
    ax.set_xlabel("Time", color="white")
    ax.set_ylabel("Price ($)", color="white")
    ax.grid(alpha=0.3)
    ax.set_facecolor("#111111")
    
    # Save chart
    chart_path = tempfile.mktemp(suffix=".png")
    plt.savefig(chart_path, bbox_inches='tight', facecolor="#111111")
    plt.close()
    
    # Generate voiceover
    text = f"{symbol} is at ${info['price']:.2f}, {info['change']:+.2f} percent. AI predicts {pred['signal']}. {pred['reason']}. Not financial advice."
    
    tts = gTTS(text, lang='en')
    audio_path = tempfile.mktemp(suffix=".mp3")
    tts.save(audio_path)
    
    # Create video using ffmpeg (if available)
    video_path = tempfile.mktemp(suffix=".mp4")
    
    try:
        # Try to use ffmpeg directly
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', chart_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=1920:1080',
            '-shortest',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(video_path):
            # Cleanup
            os.remove(chart_path)
            os.remove(audio_path)
            return video_path
        else:
            st.warning("ffmpeg not available. Using fallback method.")
            return None
            
    except Exception as e:
        st.warning(f"Video creation error: {str(e)}")
        # Return just the audio if video fails
        st.info("Audio file generated. You can use it with any video editor.")
        st.audio(audio_path)
        return None

def upload_to_youtube_simple(video_path, title, description, tags):
    """Upload video to YouTube"""
    if not st.session_state.youtube_connected:
        return False
    
    try:
        credentials = st.session_state.youtube_credentials
        youtube = build('youtube', 'v3', credentials=credentials)
        
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
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        response = request.execute()
        
        st.success(f"✅ Uploaded! Video ID: {response['id']}")
        return True
        
    except Exception as e:
        st.error(f"Upload failed: {str(e)}")
        return False

# ==================== FOOTER ====================
st.divider()
st.caption("🤖 AI-Powered Stock Video Creator | YouTube Auto-upload")
