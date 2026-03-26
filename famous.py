import streamlit as st
import os
import time
import tempfile
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from PIL import Image
import requests
import json
from gtts import gTTS
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip
import asyncio
import threading
import schedule

# Set page config
st.set_page_config(
    page_title="AI Stock Video Creator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
</style>
""", unsafe_allow_html=True)

# Title
st.title("📈 AI-Powered Stock Video Creator")
st.caption("Automatic video generation for stocks with AI predictions | Posts to YouTube, TikTok, Instagram, X & more")

# Initialize session state
if 'generated_videos' not in st.session_state:
    st.session_state.generated_videos = []
if 'posting_status' not in st.session_state:
    st.session_state.posting_status = {}

# Stock list
STOCKS = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "AMD"]

# Sidebar - API Keys
with st.sidebar:
    st.header("🔑 API Configuration")
    
    st.subheader("Ayrshare API (Recommended)")
    ayrshare_key = st.text_input(
        "Ayrshare API Key",
        type="password",
        placeholder="Get from app.ayrshare.com",
        help="Posts to 10+ platforms with one API call"
    )
    
    st.divider()
    st.subheader("YouTube (OAuth 2.0)")
    uploaded_file = st.file_uploader("Upload client_secrets.json", type=['json'])
    if uploaded_file:
        secrets_path = tempfile.mktemp(suffix=".json")
        with open(secrets_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        st.session_state.youtube_secrets = secrets_path
        st.success("✅ YouTube credentials uploaded!")
    
    st.divider()
    st.subheader("TikTok (Cookie Method)")
    tiktok_session = st.text_input("TikTok Session ID", type="password")
    
    st.divider()
    st.subheader("Other Platforms")
    st.info("Ayrshare handles: X/Twitter, Instagram, LinkedIn, Facebook, Reddit, Pinterest, Telegram")
    
    st.divider()
    st.markdown("### 📊 Stock Selection")
    selected_stocks = st.multiselect("Select stocks to monitor", STOCKS, default=STOCKS[:4])

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🎬 Video Generation")
    
    # Manual generation
    manual_symbol = st.selectbox("Generate video for specific stock", ["Select a stock"] + STOCKS)
    
    col_orient1, col_orient2 = st.columns(2)
    with col_orient1:
        orientation = st.radio("Video Orientation", ["Horizontal (YouTube)", "Vertical (TikTok/Reels)"], index=0)
    
    if st.button("🚀 Generate Video Now", type="primary", use_container_width=True):
        if manual_symbol != "Select a stock":
            with st.spinner(f"Generating video for {manual_symbol}..."):
                try:
                    video_path = generate_video(
                        manual_symbol, 
                        "vertical" if "Vertical" in orientation else "horizontal"
                    )
                    if video_path:
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
    
    # Auto-posting section
    st.header("📱 Auto-Post to Platforms")
    
    col_x, col_yt, col_tt = st.columns(3)
    with col_x:
        post_x = st.checkbox("X (Twitter)", value=True)
    with col_yt:
        post_youtube = st.checkbox("YouTube", value=True)
    with col_tt:
        post_tiktok = st.checkbox("TikTok", value=True)
    
    if st.button("🤖 Start Auto-Generation & Posting", type="secondary"):
        if ayrshare_key:
            st.info("Starting auto-generation job (runs every 5 minutes)")
            # Start background thread
            start_auto_generation(selected_stocks, ayrshare_key, tiktok_session)
        else:
            st.error("Please enter Ayrshare API key for auto-posting")

with col2:
    st.header("📊 Stock Dashboard")
    
    # Display stock data
    for symbol in selected_stocks[:4]:
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
            </div>
            """, unsafe_allow_html=True)
        except:
            pass

# Video generation function
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
    """Simple AI prediction based on price action"""
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

def generate_video(symbol, orientation="horizontal"):
    """Generate stock video with AI voiceover"""
    
    # Get data
    info = get_stock_data(symbol)
    if not info:
        return None
    
    pred = get_prediction(info)
    
    # Set dimensions
    if orientation == "vertical":
        size = (1080, 1920)
        title = f"🚨 {symbol} AI ALERT"
        font_size = 90
    else:
        size = (1920, 1080)
        title = f"{symbol} Live • AI Prediction"
        font_size = 120
    
    # Create chart
    data = yf.download(symbol, period="1d", interval="5m")
    if data.empty:
        # Fallback to mock data
        dates = pd.date_range(start=datetime.now() - timedelta(hours=6), periods=72, freq='5min')
        data = pd.DataFrame({'Close': np.random.normal(info['price'], info['price']*0.01, 72)}, index=dates)
    
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
        
        # Cleanup
        os.remove(chart_path)
        os.remove(audio_path)
        
        return video_path
        
    except Exception as e:
        st.error(f"Video creation error: {e}")
        return None

def post_with_ayrshare(video_path, caption, title, ayrshare_key):
    """Post to multiple platforms using Ayrshare"""
    try:
        headers = {
            "Authorization": f"Bearer {ayrshare_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "post": caption,
            "platforms": ["youtube", "tiktok", "instagram", "twitter", "facebook", "linkedin"],
            "mediaUrls": [video_path],
            "title": title,
            "youtubeTitle": title,
            "isShorts": True
        }
        
        response = requests.post(
            "https://api.ayrshare.com/api/post",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except Exception as e:
        st.error(f"Ayrshare error: {e}")
        return None

def start_auto_generation(stocks, ayrshare_key, tiktok_session):
    """Start automatic generation in background"""
    
    def generate_and_post():
        for symbol in stocks:
            try:
                # Generate videos
                horiz_video = generate_video(symbol, "horizontal")
                vert_video = generate_video(symbol, "vertical")
                
                if horiz_video and vert_video:
                    # Prepare content
                    info = get_stock_data(symbol)
                    pred = get_prediction(info)
                    
                    caption = f"""{symbol} LIVE • ${info['price']:.2f} ({info['change']:+.2f}%)
AI Prediction: {pred['signal']} — {pred['reason']}
Confidence: {pred['confidence']:.0f}%

Not financial advice • DYOR
#Stocks #{symbol} #AI #Trading"""
                    
                    title = f"{symbol} AI Stock Alert - {pred['signal']}"
                    
                    # Post using Ayrshare
                    if ayrshare_key:
                        result = post_with_ayrshare(horiz_video, caption, title, ayrshare_key)
                        if result:
                            st.session_state.posting_status[symbol] = "Posted to all platforms"
                        else:
                            st.session_state.posting_status[symbol] = "Ayrshare failed"
                    
                    # Cleanup
                    os.remove(horiz_video)
                    os.remove(vert_video)
                    
            except Exception as e:
                st.session_state.posting_status[symbol] = f"Error: {e}"
    
    # Run once
    generate_and_post()
    
    # Schedule for every 5 minutes
    schedule.every(5).minutes.do(generate_and_post)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(1)

# Manual posting section
with st.expander("📤 Manual Post to Platforms"):
    if st.session_state.generated_videos:
        latest_video = st.session_state.generated_videos[-1]
        st.video(latest_video)
        
        custom_caption = st.text_area("Customize caption", 
            "AI Stock Prediction - Not financial advice #Stocks #AI")
        
        if st.button("Post Now to All Platforms"):
            if ayrshare_key:
                result = post_with_ayrshare(
                    latest_video, 
                    custom_caption, 
                    "AI Stock Alert",
                    ayrshare_key
                )
                if result:
                    st.success("✅ Posted to all platforms!")
                else:
                    st.error("Posting failed")
            else:
                st.error("Please enter Ayrshare API key")

# Footer
st.divider()
st.caption("🤖 AI-Powered Stock Video Creator | Generates videos with real-time data and AI predictions")
st.caption("💡 Install: pip install streamlit yfinance matplotlib pandas gtts moviepy requests schedule")

# Requirements info
with st.expander("📦 Required Packages"):
    st.code("""
pip install streamlit yfinance matplotlib pandas gtts moviepy requests schedule pillow
    """)
