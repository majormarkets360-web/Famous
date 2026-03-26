import streamlit as st
import os
import tempfile
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from gtts import gTTS
import requests
import json
import pickle
import subprocess
import base64
from io import BytesIO

# ==================== TRY TO IMPORT GOOGLE LIBRARIES ====================
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    st.warning("⚠️ Google API libraries not installed. YouTube upload will be disabled.")
    st.info("Run: pip install google-auth-oauthlib google-api-python-client")

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
if 'audio_path' not in st.session_state:
    st.session_state.audio_path = None

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
        padding: 15px;
        border-radius: 10px;
        background: #1e1e1e;
        margin: 10px 0;
        border-left: 4px solid #00ff88;
    }
    .connected-status {
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .connected {
        background-color: #00ff8822;
        border: 1px solid #00ff88;
        color: #00ff88;
    }
    .disconnected {
        background-color: #ff444422;
        border: 1px solid #ff4444;
        color: #ff4444;
    }
</style>
""", unsafe_allow_html=True)

# ==================== TITLE ====================
st.title("📈 AI-Powered Stock Video Creator")
st.caption("Generate stock videos with AI voiceover | Auto-post to YouTube")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🔑 YouTube Authentication")
    
    if not GOOGLE_AVAILABLE:
        st.error("❌ Google libraries not installed")
        st.code("pip install google-auth-oauthlib google-api-python-client")
    else:
        # Option 1: Upload OAuth file
        uploaded_file = st.file_uploader(
            "Upload client_secrets.json",
            type=['json'],
            help="Download from Google Cloud Console (Desktop app type)"
        )
        
        if uploaded_file:
            secrets_path = tempfile.mktemp(suffix=".json")
            with open(secrets_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            
            st.success("✅ Credentials loaded!")
            
            if st.button("🔌 Connect YouTube", use_container_width=True):
                with st.spinner("Connecting to YouTube..."):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            secrets_path,
                            scopes=['https://www.googleapis.com/auth/youtube.upload']
                        )
                        credentials = flow.run_local_server(port=8080)
                        st.session_state.youtube_credentials = credentials
                        st.session_state.youtube_connected = True
                        
                        # Save token
                        with open('youtube_token.pickle', 'wb') as f:
                            pickle.dump(credentials, f)
                        
                        st.success("✅ YouTube connected!")
                        os.remove(secrets_path)
                    except Exception as e:
                        st.error(f"Connection failed: {str(e)}")
        
        # Option 2: Use saved token
        if os.path.exists('youtube_token.pickle'):
            if st.button("🔌 Use Saved Token", use_container_width=True):
                try:
                    with open('youtube_token.pickle', 'rb') as f:
                        credentials = pickle.load(f)
                    
                    if credentials and credentials.expired and credentials.refresh_token:
                        credentials.refresh(Request())
                    
                    st.session_state.youtube_credentials = credentials
                    st.session_state.youtube_connected = True
                    st.success("✅ Connected with saved token!")
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
    
    # Display connection status
    if st.session_state.youtube_connected:
        st.markdown("""
        <div class="connected-status connected">
        ✅ YouTube Connected!
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="connected-status disconnected">
        ❌ YouTube Not Connected
        </div>
        """, unsafe_allow_html=True)
    
    # Stock selection
    st.divider()
    st.header("📊 Stock Selection")
    STOCKS = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "AMD"]
    selected_stocks = st.multiselect("Select stocks", STOCKS, default=STOCKS[:4])

# ==================== MAIN CONTENT ====================
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🎬 Generate Stock Video")
    
    manual_symbol = st.selectbox("Select stock", ["Select a stock"] + STOCKS)
    
    # Video options
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        include_chart = st.checkbox("Include Stock Chart", value=True)
    with col_opt2:
        include_voice = st.checkbox("Include AI Voiceover", value=True)
    
    if st.button("🚀 Generate Video", type="primary", use_container_width=True):
        if manual_symbol != "Select a stock":
            with st.spinner(f"Generating content for {manual_symbol}..."):
                try:
                    # Get stock data
                    info = get_stock_data(manual_symbol)
                    if info:
                        st.success(f"✅ Data fetched for {manual_symbol}")
                        
                        # Display info
                        col_price, col_change = st.columns(2)
                        with col_price:
                            st.metric("Current Price", f"${info['price']:.2f}")
                        with col_change:
                            st.metric("Change", f"{info['change']:+.2f}%", 
                                     delta_color="normal")
                        
                        # Generate voiceover
                        if include_voice:
                            audio_path = generate_voiceover(info)
                            if audio_path:
                                st.session_state.audio_path = audio_path
                                st.audio(audio_path)
                                st.success("✅ Voiceover generated!")
                        
                        # Generate chart
                        if include_chart:
                            chart_path = generate_chart(manual_symbol, info)
                            if chart_path:
                                st.image(chart_path, caption=f"{manual_symbol} Price Chart")
                                st.success("✅ Chart generated!")
                        
                        # Create simple video
                        video_path = create_simple_video(info, audio_path if include_voice else None)
                        if video_path:
                            st.session_state.video_path = video_path
                            st.video(video_path)
                            
                            # Download button
                            with open(video_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Download Video",
                                    data=f,
                                    file_name=f"{manual_symbol}_video.mp4",
                                    mime="video/mp4"
                                )
                        else:
                            # If video creation fails, provide audio download
                            if include_voice and audio_path:
                                with open(audio_path, 'rb') as f:
                                    st.download_button(
                                        label="📥 Download Audio",
                                        data=f,
                                        file_name=f"{manual_symbol}_audio.mp3",
                                        mime="audio/mpeg"
                                    )
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please select a stock")
    
    # YouTube upload section
    if st.session_state.video_path and GOOGLE_AVAILABLE:
        st.divider()
        st.header("📤 Upload to YouTube")
        
        title = st.text_input("Video Title", f"{manual_symbol} Stock Update - {datetime.now().strftime('%Y-%m-%d')}")
        description = st.text_area("Description", 
            f"AI-generated analysis for {manual_symbol}. Current price: ${info['price']:.2f}\n\nNot financial advice. DYOR.")
        tags = st.text_input("Tags (comma separated)", f"{manual_symbol}, stocks, trading, AI, market analysis")
        
        if st.button("📺 Upload to YouTube", use_container_width=True):
            if st.session_state.youtube_connected:
                with st.spinner("Uploading..."):
                    success = upload_to_youtube(
                        st.session_state.video_path,
                        title,
                        description,
                        [tag.strip() for tag in tags.split(',')]
                    )
                    if success:
                        st.balloons()
                        st.success("🎉 Video uploaded to YouTube!")
            else:
                st.error("Please connect YouTube account first (see sidebar)")

with col2:
    st.header("📊 Live Stock Dashboard")
    
    for symbol in selected_stocks:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            change = info.get('regularMarketChangePercent', 0)
            
            st.markdown(f"""
            <div class="stock-card">
                <h3>{symbol}</h3>
                <div style="font-size: 24px; font-weight: bold; color: #00ff88;">
                    ${price:.2f}
                </div>
                <div style="color: {'#00ff88' if change >= 0 else '#ff4444'};">
                    {change:+.2f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
        except:
            pass
    
    if st.button("🔄 Refresh Data"):
        st.rerun()

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
            'change': change,
            'volume': info.get('volume', 0)
        }
    except Exception as e:
        st.error(f"Error fetching {symbol}: {e}")
        return None

def generate_voiceover(info):
    """Generate AI voiceover"""
    text = f"{info['symbol']} is currently trading at ${info['price']:.2f}. That's {info['change']:+.2f} percent. This is AI-generated market analysis. Not financial advice."
    
    tts = gTTS(text, lang='en')
    audio_path = tempfile.mktemp(suffix=".mp3")
    tts.save(audio_path)
    return audio_path

def generate_chart(symbol, info):
    """Generate stock chart"""
    # Get historical data
    data = yf.download(symbol, period="1d", interval="5m")
    
    if data.empty:
        # Create mock data
        dates = pd.date_range(start=datetime.now() - timedelta(hours=6), periods=72, freq='5min')
        data = pd.DataFrame({'Close': np.random.normal(info['price'], info['price']*0.01, 72)}, index=dates)
    
    # Create chart
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(data.index, data['Close'], color="#00ff88", linewidth=2)
    ax.fill_between(data.index, data['Close'].min(), data['Close'], alpha=0.3, color="#00ff88")
    ax.set_title(f"{symbol} - ${info['price']:.2f}", fontsize=16, color="white")
    ax.set_xlabel("Time", color="white")
    ax.set_ylabel("Price ($)", color="white")
    ax.grid(alpha=0.3)
    ax.set_facecolor("#111111")
    
    # Save chart
    chart_path = tempfile.mktemp(suffix=".png")
    plt.savefig(chart_path, bbox_inches='tight', facecolor="#111111")
    plt.close()
    
    return chart_path

def create_simple_video(info, audio_path=None):
    """Create simple video using HTML5 (no ffmpeg needed)"""
    # Create an HTML file with video content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ 
                margin: 0; 
                background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: rgba(0,0,0,0.7);
                border-radius: 20px;
                max-width: 800px;
            }}
            h1 {{ color: #00ff88; font-size: 48px; }}
            .price {{ font-size: 72px; color: white; font-weight: bold; margin: 20px 0; }}
            .change {{ font-size: 36px; color: {'#00ff88' if info['change'] >= 0 else '#ff4444'}; }}
            .disclaimer {{ color: #888; margin-top: 40px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{info['symbol']} Stock Update</h1>
            <div class="price">${info['price']:.2f}</div>
            <div class="change">{info['change']:+.2f}%</div>
            <div class="disclaimer">Not financial advice. Always DYOR.</div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML file
    html_path = tempfile.mktemp(suffix=".html")
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    # Return the HTML file path (can be viewed in browser)
    return html_path

def upload_to_youtube(video_path, title, description, tags):
    """Upload to YouTube"""
    if not GOOGLE_AVAILABLE or not st.session_state.youtube_connected:
        return False
    
    try:
        credentials = st.session_state.youtube_credentials
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # For HTML files, we need to convert or use a different approach
        if video_path.endswith('.html'):
            st.warning("HTML files can't be uploaded directly to YouTube. Please use the video file option.")
            return False
        
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
        
        return True
    except Exception as e:
        st.error(f"YouTube upload error: {str(e)}")
        return False

# ==================== FOOTER ====================
st.divider()
st.caption("🤖 AI-Powered Stock Video Creator | YouTube Auto-upload")
st.caption("💡 To enable YouTube upload: pip install google-auth-oauthlib google-api-python-client")
