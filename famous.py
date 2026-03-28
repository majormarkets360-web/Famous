import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import time
import warnings
import os
import tempfile
from social_manager import SocialMediaManager

warnings.filterwarnings('ignore')

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="AI Trading Dashboard", page_icon="📈", layout="wide")

# ========== INITIALIZE SESSION STATE ==========
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT']
if 'exchange_data' not in st.session_state:
    st.session_state.exchange_data = {}
if 'sector_data' not in st.session_state:
    st.session_state.sector_data = {}
if 'ai_predictions' not in st.session_state:
    st.session_state.ai_predictions = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'auto_stream' not in st.session_state:
    st.session_state.auto_stream = False
if 'broadcast_active' not in st.session_state:
    st.session_state.broadcast_active = False
if 'social_manager' not in st.session_state:
    st.session_state.social_manager = SocialMediaManager()

# ========== EXCHANGE CONFIGURATION ==========
EXCHANGES = {
    "🇺🇸 NYSE": {"indices": "^NYA", "city": "New York"},
    "📊 NASDAQ": {"indices": "^IXIC", "city": "New York"},
    "🇨🇳 Shanghai": {"indices": "000001.SS", "city": "Shanghai"},
    "🇯🇵 Japan": {"indices": "^N225", "city": "Tokyo"},
    "🇪🇺 Euronext": {"indices": "^FCHI", "city": "Paris"},
    "🇭🇰 Hong Kong": {"indices": "^HSI", "city": "Hong Kong"},
    "🇮🇳 India": {"indices": "^NSEI", "city": "Mumbai"},
    "🇬🇧 London": {"indices": "^FTSE", "city": "London"}
}

SECTORS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Consumer": "XLY",
    "Industrials": "XLI",
    "Energy": "XLE"
}

# ========== HELPER FUNCTIONS ==========
def get_exchange_time(city):
    try:
        import pytz
        tz_map = {"New York": "America/New_York", "Shanghai": "Asia/Shanghai", "Tokyo": "Asia/Tokyo",
                  "Paris": "Europe/Paris", "Hong Kong": "Asia/Hong_Kong", "Mumbai": "Asia/Kolkata",
                  "London": "Europe/London"}
        tz = pytz.timezone(tz_map.get(city, "UTC"))
        return datetime.now(tz).strftime("%H:%M")
    except:
        return "--:--"

def fetch_exchange_data():
    data = {}
    for name, config in EXCHANGES.items():
        try:
            ticker = yf.Ticker(config['indices'])
            hist = ticker.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[0]
                change = ((current - prev) / prev * 100) if prev else 0
                data[name] = {'value': current, 'change': change}
        except:
            pass
    return data

def fetch_sector_data():
    data = {}
    for name, etf in SECTORS.items():
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[0]
                perf = ((current - prev) / prev * 100) if prev else 0
                signal = "BUY" if perf > 1 else "SELL" if perf < -1 else "HOLD"
                data[name] = {'performance': perf, 'signal': signal}
        except:
            pass
    return data

def update_all_data():
    with st.spinner("Updating market data..."):
        st.session_state.exchange_data = fetch_exchange_data()
        st.session_state.sector_data = fetch_sector_data()
        st.session_state.last_update = datetime.now()
    return True

# ========== CSS ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a2a, #1a1a3a);
    }
    .exchange-card, .stat-card, .sector-card {
        background: rgba(26, 26, 46, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .stat-value { font-size: 32px; font-weight: 700; color: #00ff88; }
    .stat-label { color: #888; font-size: 14px; }
    .market-name { font-size: 16px; font-weight: 600; color: #00ff88; }
    .market-value { font-size: 28px; font-weight: 700; color: white; }
    .sector-name { font-weight: 600; }
    .sector-perf { font-size: 18px; font-weight: 700; }
    .stButton > button {
        background: linear-gradient(135deg, #00ff88, #00cc66);
        color: black;
        font-weight: 600;
        border-radius: 25px;
    }
    .live-badge {
        background: linear-gradient(90deg, #ff3366, #ff0066);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    .main-header {
        background: rgba(10, 10, 42, 0.9);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border-bottom: 2px solid #00ff88;
    }
    [data-testid="stSidebar"] {
        background: rgba(10, 10, 42, 0.95);
        backdrop-filter: blur(10px);
    }
    .timezone-ticker {
        background: rgba(0,0,0,0.5);
        border-radius: 30px;
        padding: 8px 15px;
        margin: 10px 0;
        overflow: hidden;
        white-space: nowrap;
    }
    .timezone-ticker-content {
        display: inline-block;
        animation: ticker 50s linear infinite;
    }
    @keyframes ticker {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    .ticker-item {
        display: inline-block;
        margin: 0 20px;
    }
    .ad-container {
        background: rgba(0,0,0,0.6);
        border: 1px solid rgba(0,255,136,0.3);
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin: 10px 0;
    }
    .ad-title { color: #00ff88; font-size: 12px; font-weight: bold; }
    .ad-button {
        background: #00ff88;
        color: black;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
        font-size: 10px;
        margin-top: 8px;
    }
    .stock-ticker {
        background: rgba(0,0,0,0.6);
        border-radius: 16px;
        padding: 15px;
        margin: 10px 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ====================
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between;">
        <div>
            <h1 style="color: #00ff88; margin: 0;">AI Trading Dashboard</h1>
            <p style="color: #888;">Real-time Analysis | Auto-Broadcast</p>
        </div>
        <div><span class="live-badge">🔴 LIVE</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== TIMEZONE TICKER ====================
ticker_parts = []
for name, config in EXCHANGES.items():
    time_str = get_exchange_time(config['city'])
    ticker_parts.append(f"<span class='ticker-item'>🌍 {config['city']}: {time_str}</span>")

st.markdown(f"""
<div class="timezone-ticker">
    <div class="timezone-ticker-content">
        {' '.join(ticker_parts)}
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== CONTROL BUTTONS ====================
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🔄 Update Data", use_container_width=True):
        update_all_data()
        st.success("Updated!")
with col2:
    if st.button("▶️ Start Stream" if not st.session_state.auto_stream else "⏸️ Stop Stream", use_container_width=True):
        st.session_state.auto_stream = not st.session_state.auto_stream
with col3:
    if st.button("📢 Start Broadcast" if not st.session_state.broadcast_active else "🔴 Stop Broadcast", use_container_width=True):
        st.session_state.broadcast_active = not st.session_state.broadcast_active
with col4:
    st.markdown(f"<div style='text-align:center; padding:8px; background:rgba(26,26,46,0.7); border-radius:30px;'><small>Updated: {st.session_state.last_update.strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)

# ==================== MAIN LAYOUT ====================
left_col, right_col = st.columns([2.5, 1])

with right_col:
    # Stock Ticker
    st.markdown('<div class="stock-ticker"><h4 style="color:#00ff88; margin:0 0 10px 0;">📊 MARKET MOVERS</h4>', unsafe_allow_html=True)
    
    # Create rotating stock data
    stocks = []
    for name, data in st.session_state.exchange_data.items():
        stocks.append({'name': name.split()[0], 'value': data['value'], 'change': data['change']})
    
    if stocks:
        import random
        random.shuffle(stocks)
        for stock in stocks[:3]:
            change_class = "positive" if stock['change'] >= 0 else "negative"
            change_symbol = "+" if stock['change'] >= 0 else ""
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                <span style="color:#00ff88;">{stock['name']}</span>
                <span>${stock['value']:.2f}</span>
                <span class="{change_class}">{change_symbol}{stock['change']:.1f}%</span>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Ad Placeholders
    ads = [
        ("📢", "SPONSORED", "Your Ad Here"),
        ("📊", "PREMIUM", "AI Pro Analytics"),
        ("📚", "FREE TRAINING", "Master Markets"),
        ("🤝", "PARTNER", "Zero Commission")
    ]
    for icon, title, text in ads:
        st.markdown(f"""
        <div class="ad-container">
            <div style="font-size:28px;">{icon}</div>
            <div class="ad-title">{title}</div>
            <div style="font-size:12px;">{text}</div>
            <div class="ad-button">Learn More →</div>
        </div>
        """, unsafe_allow_html=True)

with left_col:
    # Stats Row
    stats = st.columns(4)
    with stats[0]:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{len(st.session_state.exchange_data)}</div><div class='stat-label'>Exchanges</div></div>", unsafe_allow_html=True)
    with stats[1]:
        buy = sum(1 for d in st.session_state.sector_data.values() if d.get('signal') == "BUY")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#00ff88;'>{buy}</div><div class='stat-label'>Buy Signals</div></div>", unsafe_allow_html=True)
    with stats[2]:
        sell = sum(1 for d in st.session_state.sector_data.values() if d.get('signal') == "SELL")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#ff4444;'>{sell}</div><div class='stat-label'>Sell Signals</div></div>", unsafe_allow_html=True)
    with stats[3]:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>85%</div><div class='stat-label'>AI Confidence</div></div>", unsafe_allow_html=True)
    
    # Market Overview
    st.markdown("## 📊 Market Overview")
    mkt_cols = st.columns(2)
    for idx, (name, data) in enumerate(st.session_state.exchange_data.items()):
        with mkt_cols[idx % 2]:
            change_class = "positive" if data['change'] >= 0 else "negative"
            st.markdown(f"""
            <div class="exchange-card">
                <div class="market-name">{name}</div>
                <div class="market-value">{data['value']:.2f}</div>
                <div class="{change_class}">{data['change']:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Sector Performance
    st.markdown("## 📈 Sector Performance")
    sector_cols = st.columns(4)
    for idx, (name, data) in enumerate(st.session_state.sector_data.items()):
        with sector_cols[idx % 4]:
            color = "#00ff88" if data['performance'] > 0 else "#ff4444"
            st.markdown(f"""
            <div class="sector-card">
                <div class="sector-name">{name}</div>
                <div class="sector-perf" style="color:{color};">{data['performance']:+.1f}%</div>
                <div style="font-size:11px;">{data['signal']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Controls")
    
    # Status
    if st.session_state.auto_stream:
        st.success("🟢 Stream: ACTIVE")
    else:
        st.warning("⚪ Stream: INACTIVE")
    
    if st.session_state.broadcast_active:
        st.success("📢 Broadcast: ACTIVE")
    else:
        st.warning("🔇 Broadcast: INACTIVE")
    
    st.divider()
    
    # Stats
    st.markdown("### 📊 Stats")
    st.metric("Exchanges", len(st.session_state.exchange_data))
    st.metric("Sectors", len(st.session_state.sector_data))
    
    st.divider()
    
    # Social Media Connection
    st.markdown("### 🌐 Social Media")
    
    # Twitter
    with st.expander("🐦 Twitter/X"):
        tw_key = st.text_input("API Key", type="password", key="tw_key")
        tw_secret = st.text_input("API Secret", type="password", key="tw_secret")
        tw_token = st.text_input("Access Token", type="password", key="tw_token")
        tw_token_secret = st.text_input("Access Secret", type="password", key="tw_token_secret")
        if st.button("Connect Twitter"):
            if all([tw_key, tw_secret, tw_token, tw_token_secret]):
                success, msg = st.session_state.social_manager.connect_twitter(
                    tw_key, tw_secret, tw_token, tw_token_secret
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # YouTube
    with st.expander("📺 YouTube"):
        youtube_file = st.file_uploader("Upload client_secrets.json", type=['json'])
        if youtube_file:
            secrets_path = tempfile.mktemp(suffix=".json")
            with open(secrets_path, 'wb') as f:
                f.write(youtube_file.getvalue())
            if st.button("Connect YouTube"):
                success, msg = st.session_state.social_manager.connect_youtube(secrets_path)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # Facebook
    with st.expander("📘 Facebook"):
        fb_token = st.text_input("Access Token", type="password", key="fb_token")
        fb_page = st.text_input("Page ID", key="fb_page")
        if st.button("Connect Facebook"):
            if fb_token:
                success, msg = st.session_state.social_manager.connect_facebook(fb_token, fb_page)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # Instagram
    with st.expander("📷 Instagram"):
        ig_token = st.text_input("Access Token", type="password", key="ig_token")
        ig_account = st.text_input("Account ID", key="ig_account")
        if st.button("Connect Instagram"):
            if ig_token and ig_account:
                success, msg = st.session_state.social_manager.connect_instagram(ig_token, ig_account)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # TikTok
    with st.expander("🎵 TikTok"):
        tt_session = st.text_input("Session ID", type="password", key="tt_session")
        if st.button("Configure TikTok"):
            success, msg = st.session_state.social_manager.connect_tiktok(session_id=tt_session)
            if success:
                st.success(msg)
            else:
                st.error(msg)
    
    st.divider()
    
    # Quick Post
    st.markdown("### 📤 Quick Post")
    quick_msg = st.text_area("Message", height=80)
    if st.button("📢 Post to All", use_container_width=True):
        if quick_msg:
            with st.spinner("Posting..."):
                results = st.session_state.social_manager.post_to_all(quick_msg)
                for platform, result in results.items():
                    if result['success']:
                        st.success(f"✅ {platform}")
                    else:
                        st.error(f"❌ {platform}: {result['message']}")
        else:
            st.warning("Enter a message")

# ==================== AUTO-STREAM ====================
if st.session_state.auto_stream:
    time.sleep(30)
    st.rerun()

# ==================== INITIAL LOAD ====================
if not st.session_state.exchange_data:
    update_all_data()

# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888;">
    Auto-broadcast to Twitter, YouTube, Facebook, Instagram, TikTok | 24/7 Market Intelligence
</div>
""", unsafe_allow_html=True)
