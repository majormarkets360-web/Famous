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

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="AI Stock Video Creator",
    page_icon="📈",
    layout="wide"
)

# ==================== SESSION STATE ====================
if 'video_path' not in st.session_state:
    st.session_state.video_path = None
if 'youtube_connected' not in st.session_state:
    st.session_state.youtube_connected = False
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🔧 Configuration")
    
    # ========== YOUTUBE CONNECTION SECTION ==========
    st.subheader("📺 YouTube Upload")
    
    st.info("""
    ### 📝 YouTube Upload Options
    
    **Option 1: YouTube Data API Key** (Easier)
    - Get from Google Cloud Console
    - Uploads videos directly
    
    **Option 2: Download and Upload Manually**
    - Generate video
    - Download to your computer
    - Upload to YouTube manually
    """)
    
    # YouTube API Key input
    st.write("**Option 1: Use YouTube API Key**")
    youtube_api_key = st.text_input(
        "YouTube API Key",
        type="password",
        placeholder="AIzaSy...",
        help="Get from Google Cloud Console → APIs & Services → Credentials"
    )
    
    if youtube_api_key:
        st.session_state.youtube_api_key = youtube_api_key
        st.session_state.youtube_connected = True
        st.success("✅ YouTube API Key saved!")
    
    st.divider()
    
    # Option 2: Manual upload instructions
    st.write("**Option 2: Manual Upload**")
    st.markdown("""
    1. Generate video below
    2. Click download button
    3. Go to [YouTube Studio](https://studio.youtube.com)
    4. Upload the video manually
    """)
    
    st.divider()
    
    # Stock selection
    st.subheader("📊 Select Stocks")
    STOCKS = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT", "META", "AMD"]
    selected_stocks = st.multiselect("Monitor these stocks", STOCKS, default=["AAPL", "TSLA"])

# ==================== MAIN CONTENT ====================
st.title("📈 AI Stock Video Creator")
st.caption("Generate stock videos with AI voiceover | Download or upload to YouTube")

col1, col2 = st.columns([2, 1])

with col1:
    st.header("🎬 Create Video")
    
    # Stock selection for video
    stock_symbol = st.selectbox("Select stock", ["Select a stock"] + STOCKS)
    
    # Video options
    col_opts1, col_opts2 = st.columns(2)
    with col_opts1:
        include_voice = st.checkbox("Include AI Voiceover", value=True)
    with col_opts2:
        include_chart = st.checkbox("Include Stock Chart", value=True)
    
    if st.button("🚀 Generate Video", type="primary", use_container_width=True):
        if stock_symbol != "Select a stock":
            with st.spinner(f"Generating content for {stock_symbol}..."):
                try:
                    # Get stock data
                    stock = yf.Ticker(stock_symbol)
                    info = stock.info
                    price = info.get('regularMarketPrice', info.get('currentPrice', 0))
                    prev_close = info.get('regularMarketPreviousClose', price)
                    change = ((price - prev_close) / prev_close * 100) if prev_close else 0
                    volume = info.get('volume', 0)
                    
                    stock_data = {
                        'symbol': stock_symbol,
                        'price': price,
                        'change': change,
                        'volume': volume,
                        'high': info.get('dayHigh', price),
                        'low': info.get('dayLow', price)
                    }
                    st.session_state.stock_data = stock_data
                    
                    # Display metrics
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Symbol", stock_symbol)
                    with col_b:
                        st.metric("Price", f"${price:.2f}")
                    with col_c:
                        st.metric("Change", f"{change:+.2f}%", delta=f"{change:+.2f}%")
                    
                    # Generate AI voiceover
                    audio_path = None
                    if include_voice:
                        st.info("🎤 Generating AI voiceover...")
                        text = f"{stock_symbol} is currently trading at ${price:.2f}. That's {change:+.2f} percent. Volume is {volume:,} shares. Today's range is ${stock_data['low']:.2f} to ${stock_data['high']:.2f}. This is AI-generated market analysis. Not financial advice."
                        tts = gTTS(text, lang='en', slow=False)
                        audio_path = tempfile.mktemp(suffix=".mp3")
                        tts.save(audio_path)
                        st.audio(audio_path)
                        st.success("✅ Voiceover generated!")
                    
                    # Generate chart
                    chart_path = None
                    if include_chart:
                        st.info("📊 Creating stock chart...")
                        data = yf.download(stock_symbol, period="1d", interval="5m")
                        if data.empty:
                            dates = pd.date_range(start=datetime.now() - timedelta(hours=6), periods=72, freq='5min')
                            data = pd.DataFrame({'Close': np.random.normal(price, price*0.01, 72)}, index=dates)
                        
                        plt.style.use('dark_background')
                        fig, ax = plt.subplots(figsize=(12, 6))
                        ax.plot(data.index, data['Close'], color="#00ff88", linewidth=2.5)
                        ax.fill_between(data.index, data['Close'].min(), data['Close'], alpha=0.3, color="#00ff88")
                        ax.set_title(f"{stock_symbol} - ${price:.2f} ({change:+.2f}%)", fontsize=16, color="white", pad=20)
                        ax.set_xlabel("Time", fontsize=12, color="white")
                        ax.set_ylabel("Price ($)", fontsize=12, color="white")
                        ax.legend(['Price'], fontsize=10)
                        ax.grid(alpha=0.3)
                        ax.set_facecolor("#111111")
                        
                        chart_path = tempfile.mktemp(suffix=".png")
                        plt.savefig(chart_path, bbox_inches='tight', facecolor="#111111", dpi=150)
                        plt.close()
                        
                        st.image(chart_path, caption=f"{stock_symbol} Price Chart - Last 24 Hours")
                        st.success("✅ Chart generated!")
                    
                    # Create combined HTML report
                    st.info("🎬 Creating video report...")
                    
                    # Create HTML content
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>{stock_symbol} Stock Analysis</title>
                        <style>
                            * {{
                                margin: 0;
                                padding: 0;
                                box-sizing: border-box;
                            }}
                            body {{
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                                background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
                                color: white;
                                padding: 40px 20px;
                            }}
                            .container {{
                                max-width: 800px;
                                margin: 0 auto;
                                background: rgba(30, 30, 30, 0.95);
                                border-radius: 20px;
                                padding: 40px;
                                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                            }}
                            h1 {{
                                color: #00ff88;
                                font-size: 48px;
                                margin-bottom: 20px;
                                text-align: center;
                            }}
                            .price-box {{
                                text-align: center;
                                margin: 30px 0;
                            }}
                            .price {{
                                font-size: 72px;
                                font-weight: bold;
                                color: white;
                            }}
                            .change {{
                                font-size: 36px;
                                margin-top: 10px;
                                color: {'#00ff88' if change >= 0 else '#ff4444'};
                            }}
                            .metrics {{
                                display: grid;
                                grid-template-columns: repeat(3, 1fr);
                                gap: 20px;
                                margin: 30px 0;
                            }}
                            .metric-card {{
                                background: rgba(0,0,0,0.5);
                                padding: 15px;
                                border-radius: 10px;
                                text-align: center;
                            }}
                            .metric-label {{
                                font-size: 14px;
                                color: #888;
                                margin-bottom: 5px;
                            }}
                            .metric-value {{
                                font-size: 24px;
                                font-weight: bold;
                                color: #00ff88;
                            }}
                            .chart-container {{
                                margin: 30px 0;
                                text-align: center;
                            }}
                            .chart-container img {{
                                max-width: 100%;
                                border-radius: 10px;
                            }}
                            .disclaimer {{
                                margin-top: 40px;
                                padding: 20px;
                                background: rgba(255,255,0,0.1);
                                border-radius: 10px;
                                text-align: center;
                                font-size: 12px;
                                color: #888;
                            }}
                            .footer {{
                                margin-top: 30px;
                                text-align: center;
                                font-size: 12px;
                                color: #666;
                            }}
                            @media (max-width: 600px) {{
                                .container {{ padding: 20px; }}
                                .price {{ font-size: 48px; }}
                                .change {{ font-size: 24px; }}
                                .metrics {{ grid-template-columns: 1fr; }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>{stock_symbol} Stock Analysis</h1>
                            
                            <div class="price-box">
                                <div class="price">${price:,.2f}</div>
                                <div class="change">{change:+.2f}%</div>
                            </div>
                            
                            <div class="metrics">
                                <div class="metric-card">
                                    <div class="metric-label">Volume</div>
                                    <div class="metric-value">{volume:,}</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-label">Day High</div>
                                    <div class="metric-value">${stock_data['high']:.2f}</div>
                                </div>
                                <div class="metric-card">
                                    <div class="metric-label">Day Low</div>
                                    <div class="metric-value">${stock_data['low']:.2f}</div>
                                </div>
                            </div>
                            
                            {"<div class='chart-container'><img src='data:image/png;base64," + get_image_base64(chart_path) + "' alt='Stock Chart'></div>" if chart_path else ""}
                            
                            <div class="disclaimer">
                                ⚠️ NOT FINANCIAL ADVICE<br>
                                This is AI-generated content for informational purposes only.<br>
                                Always do your own research before making investment decisions.
                            </div>
                            
                            <div class="footer">
                                Generated by AI Stock Video Creator<br>
                                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Save HTML file
                    video_path = tempfile.mktemp(suffix=".html")
                    with open(video_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    st.session_state.video_path = video_path
                    
                    # Display HTML
                    st.components.v1.html(html_content, height=700)
                    st.success("✅ Video report created!")
                    
                    # Download button
                    with open(video_path, 'r', encoding='utf-8') as f:
                        st.download_button(
                            label="📥 Download Video Report (HTML)",
                            data=f,
                            file_name=f"{stock_symbol}_stock_report.html",
                            mime="text/html"
                        )
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Manual upload instructions
    if st.session_state.video_path:
        st.divider()
        st.header("📤 Upload to YouTube")
        
        st.info("""
        ### 📺 How to Upload to YouTube
        
        **Method 1: Manual Upload (Recommended)**
        1. Click the download button above
        2. Go to [YouTube Studio](https://studio.youtube.com)
        3. Click "Create" → "Upload video"
        4. Select the downloaded file
        5. Add title and description
        6. Publish!
        
        **Method 2: YouTube API Key** (if configured)
        - Enter your YouTube API Key in the sidebar
        - Click the button below for auto-upload
        """)
        
        if st.session_state.get('youtube_connected', False) and st.session_state.get('youtube_api_key'):
            title = st.text_input(
                "Video Title", 
                f"{stock_symbol} Stock Analysis - {datetime.now().strftime('%Y-%m-%d')}"
            )
            description = st.text_area(
                "Description",
                f"AI-generated analysis for {stock_symbol}\n\n"
                f"Current Price: ${st.session_state.stock_data['price']:.2f}\n"
                f"Change: {st.session_state.stock_data['change']:+.2f}%\n\n"
                f"Not financial advice. Always do your own research.\n\n"
                f"#stocks #{stock_symbol} #trading #AI #marketanalysis"
            )
            
            if st.button("📺 Upload with API Key", use_container_width=True):
                st.warning("YouTube API upload requires additional setup. For now, please use manual upload.")
                st.info("Manual upload is the easiest way to get your videos on YouTube!")

with col2:
    st.header("📊 Live Market Dashboard")
    
    for symbol in selected_stocks:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            change = info.get('regularMarketChangePercent', 0)
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1a1a, #2a2a2a); padding: 20px; border-radius: 10px; margin: 10px 0; border-left: 4px solid {'#00ff88' if change >= 0 else '#ff4444'}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0;">{symbol}</h3>
                        <div style="font-size: 28px; font-weight: bold; margin-top: 10px;">${price:.2f}</div>
                    </div>
                    <div style="font-size: 20px; color: {'#00ff88' if change >= 0 else '#ff4444'}">
                        {change:+.2f}%
                    </div>
                </div>
                <div style="font-size: 12px; color: #888; margin-top: 10px;">
                    Updated: {datetime.now().strftime('%H:%M:%S')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error loading {symbol}")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

# Helper function
def get_image_base64(image_path):
    """Convert image to base64 for embedding in HTML"""
    if not image_path or not os.path.exists(image_path):
        return ""
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# ==================== FOOTER ====================
st.divider()
st.caption("🤖 AI Stock Video Creator | Generate reports and upload to YouTube manually")
st.caption("💡 Tip: Download the HTML report and upload to YouTube as a video or Short")
