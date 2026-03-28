import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json
import time
import threading
import warnings
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import base64
import tempfile

# Import Social Media Manager
from social_manager import SocialMediaManager

warnings.filterwarnings('ignore')

# ========== BACKGROUND IMAGE SETUP ==========
def set_background(image_file):
    try:
        with open(image_file, "rb") as img_file:
            base64_image = base64.b64encode(img_file.read()).decode()
        return base64_image
    except:
        return None

BACKGROUND_IMAGE = None
background_file = "grok_image_1774635168261.jpg"
if os.path.exists(background_file):
    BACKGROUND_IMAGE = set_background(background_file)

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="AI Trading Dashboard", page_icon="📈", layout="wide")

# ========== INITIALIZE SESSION STATE ==========
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT', 'AMZN', 'META']
if 'exchange_data' not in st.session_state:
    st.session_state.exchange_data = {}
if 'sector_data' not in st.session_state:
    st.session_state.sector_data = {}
if 'global_alerts' not in st.session_state:
    st.session_state.global_alerts = []
if 'ai_predictions' not in st.session_state:
    st.session_state.ai_predictions = {}
if 'stream_messages' not in st.session_state:
    st.session_state.stream_messages = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'auto_stream' not in st.session_state:
    st.session_state.auto_stream = False
if 'broadcast_active' not in st.session_state:
    st.session_state.broadcast_active = False
if 'ticker_index' not in st.session_state:
    st.session_state.ticker_index = 0
if 'social_manager' not in st.session_state:
    st.session_state.social_manager = SocialMediaManager()

# ========== EXCHANGE CONFIGURATION ==========
EXCHANGES = {
    "🇺🇸 NYSE": {"indices": "^NYA", "timezone": "America/New_York", "city": "New York"},
    "📊 NASDAQ": {"indices": "^IXIC", "timezone": "America/New_York", "city": "New York"},
    "🇨🇳 Shanghai": {"indices": "000001.SS", "timezone": "Asia/Shanghai", "city": "Shanghai"},
    "🇯🇵 Japan": {"indices": "^N225", "timezone": "Asia/Tokyo", "city": "Tokyo"},
    "🇪🇺 Euronext": {"indices": "^FCHI", "timezone": "Europe/Paris", "city": "Paris"},
    "🇭🇰 Hong Kong": {"indices": "^HSI", "timezone": "Asia/Hong_Kong", "city": "Hong Kong"},
    "🇮🇳 India NSE": {"indices": "^NSEI", "timezone": "Asia/Kolkata", "city": "Mumbai"},
    "🇬🇧 London": {"indices": "^FTSE", "timezone": "Europe/London", "city": "London"}
}

# ========== HELPER FUNCTIONS ==========

def get_exchange_time(timezone_str):
    try:
        import pytz
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz).strftime("%H:%M")
    except:
        return "--:--"

def fetch_exchange_data():
    exchange_data = {}
    for name, config in EXCHANGES.items():
        try:
            index = yf.Ticker(config['indices'])
            hist = index.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[0]
                change = ((current - prev) / prev * 100) if prev else 0
                exchange_data[name] = {
                    'value': current,
                    'change': change,
                    'timestamp': datetime.now()
                }
        except:
            pass
    return exchange_data

def fetch_sector_data():
    sector_data = {}
    sectors = {"Technology": "XLK", "Financials": "XLF", "Healthcare": "XLV", 
               "Consumer": "XLY", "Industrials": "XLI", "Energy": "XLE"}
    for name, etf in sectors.items():
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[0]
                perf = ((current - prev) / prev * 100) if prev else 0
                signal = "BUY" if perf > 1 else "SELL" if perf < -1 else "HOLD"
                sector_data[name] = {'performance': perf, 'signal': signal}
        except:
            pass
    return sector_data

def update_all_data():
    with st.spinner("Updating market data..."):
        st.session_state.exchange_data = fetch_exchange_data()
        st.session_state.sector_data = fetch_sector_data()
        st.session_state.last_update = datetime.now()
    return True

# ========== CSS STYLING ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, rgba(10, 10, 42, 0.85), rgba(26, 26, 58, 0.85));
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    .exchange-card, .stat-card, .sector-card {
        background: rgba(26, 26, 46, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    
    .exchange-card:hover, .stat-card:hover, .sector-card:hover {
        border: 1px solid #00ff88;
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
    }
    
    .timezone-ticker {
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 30px;
        padding: 8px 15px;
        overflow: hidden;
        white-space: nowrap;
        margin: 10px 0;
    }
    
    .timezone-ticker-content {
        display: inline-block;
        animation: ticker 50s linear infinite;
        white-space: nowrap;
    }
    
    @keyframes ticker {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    .ticker-timezone-item {
        display: inline-block;
        margin: 0 20px;
        font-size: 14px;
    }
    
    .ticker-city { font-weight: 600; color: #00ff88; }
    .ticker-time { color: white; font-family: monospace; }
    
    .ticker-bar {
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 30px;
        padding: 8px 15px;
        overflow: hidden;
        white-space: nowrap;
        margin: 15px 0;
    }
    
    .ticker-content {
        display: inline-block;
        animation: ticker 40s linear infinite;
        white-space: nowrap;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #00ff88, #00cc66);
        color: #000;
        font-weight: 600;
        border: none;
        border-radius: 25px;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(0, 255, 136, 0.3);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 10, 42, 0.95), rgba(5, 5, 20, 0.95));
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0, 255, 136, 0.2);
    }
    
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    
    .main-header {
        background: linear-gradient(135deg, rgba(10, 10, 42, 0.9), rgba(26, 26, 58, 0.9));
        backdrop-filter: blur(10px);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border-bottom: 2px solid #00ff88;
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
    
    .stat-value { font-size: 32px; font-weight: 700; color: #00ff88; }
    .stat-label { color: #888; font-size: 14px; }
    .market-name { font-size: 16px; font-weight: 600; color: #00ff88; }
    .market-value { font-size: 28px; font-weight: 700; color: white; }
    .market-change { font-size: 14px; }
    .sector-name { font-weight: 600; margin-bottom: 5px; }
    .sector-perf { font-size: 18px; font-weight: 700; }
    
    .ad-container {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 16px;
        padding: 15px;
        text-align: center;
        margin: 12px 0;
        transition: all 0.3s ease;
    }
    
    .ad-container:hover {
        border-color: #00ff88;
        background: rgba(0, 255, 136, 0.1);
        transform: translateY(-3px);
    }
    
    .ad-icon { font-size: 28px; margin-bottom: 8px; }
    .ad-title { color: #00ff88; font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .ad-content { color: #fff; font-size: 12px; margin: 8px 0; }
    .ad-button {
        background: linear-gradient(135deg, #00ff88, #00cc66);
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 10px;
        font-weight: 600;
        display: inline-block;
    }
    
    .right-ad { position: sticky; top: 20px; }
    
    .stock-index-ticker {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 16px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .stock-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(0, 255, 136, 0.2);
    }
    
    .stock-symbol { font-weight: 600; color: #00ff88; }
    .stock-price { color: white; }
    .stock-change-positive { color: #00ff88; }
    .stock-change-negative { color: #ff4444; }
    
    .chart-container {
        background: rgba(26, 26, 46, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ====================
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; color: #00ff88;">AI Trading Dashboard</h1>
            <p style="color: #888; margin: 0;">Real-time AI Analysis | Auto-Broadcast to All Platforms</p>
        </div>
        <div><span class="live-badge">🔴 LIVE</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== TIMEZONE TICKER ====================
timezone_parts = []
for name, config in EXCHANGES.items():
    current_time = get_exchange_time(config['timezone'])
    try:
        import pytz
        tz = pytz.timezone(config['timezone'])
        hour = datetime.now(tz).hour
        status = "🟢" if 9 <= hour <= 16 else "🔴"
    except:
        status = "⚪"
    timezone_parts.append(f"<span class='ticker-timezone-item'><span class='ticker-city'>{config['city']}</span> <span class='ticker-time'>{current_time}</span> {status}</span>")

st.markdown(f"""
<div class="timezone-ticker">
    <div class="timezone-ticker-content">🌍 GLOBAL MARKET HOURS • {' • '.join(timezone_parts)} • </div>
</div>
""", unsafe_allow_html=True)

# ==================== CONTROL BUTTONS ====================
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🔄 Update Data", use_container_width=True):
        update_all_data()
        st.success("Data updated!")
with c2:
    if st.button("▶️ Start Stream" if not st.session_state.auto_stream else "⏸️ Stop Stream", use_container_width=True):
        st.session_state.auto_stream = not st.session_state.auto_stream
with c3:
    if st.button("📢 Start Broadcast" if not st.session_state.broadcast_active else "🔴 Stop Broadcast", use_container_width=True):
        st.session_state.broadcast_active = not st.session_state.broadcast_active
with c4:
    st.markdown(f"<div style='text-align: center; padding: 8px; background: rgba(26, 26, 46, 0.7); border-radius: 30px;'><small>Updated: {st.session_state.last_update.strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Dashboard Controls")
    st.success("🟢 LIVE STREAM: ACTIVE") if st.session_state.auto_stream else st.warning("⚪ LIVE STREAM: INACTIVE")
    st.success("📢 BROADCAST: ACTIVE") if st.session_state.broadcast_active else st.warning("🔇 BROADCAST: INACTIVE")
    st.divider()
    
    st.markdown("### 📊 Stats")
    st.metric("Exchanges", len(st.session_state.exchange_data))
    st.metric("Sectors", len(st.session_state.sector_data))
    st.divider()
    
    # ========== SOCIAL MEDIA SECTION ==========
    st.markdown("### 🌐 Social Media")
    
    # Twitter Connection
    with st.expander("🐦 Twitter/X", expanded=False):
        twitter_key = st.text_input("API Key", type="password", key="tw_api")
        twitter_secret = st.text_input("API Secret", type="password", key="tw_secret")
        twitter_token = st.text_input("Access Token", type="password", key="tw_token")
        twitter_token_secret = st.text_input("Access Secret", type="password", key="tw_token_secret")
        if st.button("Connect Twitter", key="conn_twitter"):
            if all([twitter_key, twitter_secret, twitter_token, twitter_token_secret]):
                success, msg = st.session_state.social_manager.connect_twitter(
                    twitter_key, twitter_secret, twitter_token, twitter_token_secret
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # YouTube Connection
    with st.expander("📺 YouTube", expanded=False):
        youtube_file = st.file_uploader("Upload client_secrets.json", type=['json'], key="youtube_secrets")
        if youtube_file:
            secrets_path = tempfile.mktemp(suffix=".json")
            with open(secrets_path, 'wb') as f:
                f.write(youtube_file.getvalue())
            if st.button("Connect YouTube", key="conn_youtube"):
                success, msg = st.session_state.social_manager.connect_youtube(secrets_path)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # Facebook Connection
    with st.expander("📘 Facebook", expanded=False):
        fb_token = st.text_input("Access Token", type="password", key="fb_token")
        fb_page = st.text_input("Page ID", key="fb_page")
        if st.button("Connect Facebook", key="conn_facebook"):
            if fb_token:
                success, msg = st.session_state.social_manager.connect_facebook(fb_token, fb_page)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # Instagram Connection
    with st.expander("📷 Instagram", expanded=False):
        ig_token = st.text_input("Access Token", type="password", key="ig_token")
        ig_account = st.text_input("Business Account ID", key="ig_account")
        if st.button("Connect Instagram", key="conn_instagram"):
            if ig_token and ig_account:
                success, msg = st.session_state.social_manager.connect_instagram(ig_token, ig_account)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # TikTok Connection
    with st.expander("🎵 TikTok", expanded=False):
        tt_session = st.text_input("Session ID", type="password", key="tt_session")
        if st.button("Configure TikTok", key="conn_tiktok"):
            success, msg = st.session_state.social_manager.connect_tiktok(session_id=tt_session)
            if success:
                st.success(msg)
            else:
                st.error(msg)
    
    # Connection Status
    st.markdown("#### Connected Platforms")
    connected = st.session_state.social_manager.get_connected_platforms()
    if connected:
        for platform in connected:
            st.success(f"✅ {platform.capitalize()}")
    else:
        st.warning("No platforms connected")
    
    st.divider()
    
    # Post Section
    st.markdown("### 📤 Quick Post")
    quick_message = st.text_area("Message", height=80, placeholder="Share market insights...")
    if st.button("📢 Post to All", use_container_width=True):
        if quick_message:
            with st.spinner("Posting..."):
                results = st.session_state.social_manager.post_to_all(quick_message)
                for platform, result in results.items():
                    if result['success']:
                        st.success(f"✅ {platform}: {result['message']}")
                    else:
                        st.error(f"❌ {platform}: {result['message']}")
        else:
            st.warning("Enter a message")

# ==================== MAIN CONTENT ====================
main_left, main_right = st.columns([2.5, 1])

with main_right:
    # Rotating Stock Index
    st.markdown("""
    <div class="stock-index-ticker">
        <div style="text-align: center; margin-bottom: 10px;">
            <span style="color: #00ff88; font-weight: 600;">📊 MARKET MOVERS</span>
        </div>
    """, unsafe_allow_html=True)
    
    all_stocks = []
    for name, data in st.session_state.exchange_data.items():
        all_stocks.append({'symbol': name.split()[0], 'price': data['value'], 'change': data['change']})
    
    if all_stocks:
        st.session_state.ticker_index = (st.session_state.ticker_index + 1) % len(all_stocks)
        stock = all_stocks[st.session_state.ticker_index]
        change_class = "stock-change-positive" if stock['change'] >= 0 else "stock-change-negative"
        change_symbol = "+" if stock['change'] >= 0 else ""
        st.markdown(f"""
        <div class="stock-item">
            <span class="stock-symbol">{stock['symbol']}</span>
            <span class="stock-price">${stock['price']:.2f}</span>
            <span class="{change_class}">{change_symbol}{stock['change']:.1f}%</span>
        </div>
        <div style="text-align: center; font-size: 10px; color: #888; margin-top: 8px;">⟳ Rotating</div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Ad Placeholders
    st.markdown("""
    <div class="right-ad">
        <div class="ad-container"><div class="ad-icon">📢</div><div class="ad-title">SPONSORED</div><div class="ad-content"><strong>Your Ad Here</strong></div><div class="ad-button">Advertise →</div></div>
        <div class="ad-container"><div class="ad-icon">📊</div><div class="ad-title">PREMIUM</div><div class="ad-content"><strong>AI Pro Analytics</strong></div><div class="ad-button">Learn More →</div></div>
        <div class="ad-container"><div class="ad-icon">📚</div><div class="ad-title">FREE TRAINING</div><div class="ad-content"><strong>Master Markets</strong></div><div class="ad-button">Register →</div></div>
        <div class="ad-container"><div class="ad-icon">🤝</div><div class="ad-title">PARTNER OFFER</div><div class="ad-content"><strong>Zero Commission</strong></div><div class="ad-button">Claim →</div></div>
    </div>
    """, unsafe_allow_html=True)

with main_left:
    # Stats Row
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{len(st.session_state.exchange_data)}</div><div class='stat-label'>Global Exchanges</div></div>", unsafe_allow_html=True)
    with stat_cols[1]:
        buy_signals = sum(1 for d in st.session_state.sector_data.values() if d.get('signal') == "BUY")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#00ff88;'>{buy_signals}</div><div class='stat-label'>Buy Signals</div></div>", unsafe_allow_html=True)
    with stat_cols[2]:
        sell_signals = sum(1 for d in st.session_state.sector_data.values() if d.get('signal') == "SELL")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#ff4444;'>{sell_signals}</div><div class='stat-label'>Sell Signals</div></div>", unsafe_allow_html=True)
    with stat_cols[3]:
        avg_conf = 75
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{avg_conf}%</div><div class='stat-label'>AI Confidence</div></div>", unsafe_allow_html=True)
    
    # Market Overview
    st.markdown("## 📊 Market Overview")
    market_cols = st.columns(2)
    for idx, (name, data) in enumerate(st.session_state.exchange_data.items()):
        with market_cols[idx % 2]:
            change_class = "positive" if data['change'] >= 0 else "negative"
            st.markdown(f"<div class='exchange-card'><div class='market-name'>{name}</div><div class='market-value'>{data['value']:.2f}</div><div class='market-change {change_class}'>{data['change']:+.2f}%</div></div>", unsafe_allow_html=True)
    
    # Sector Performance
    st.markdown("## 📈 Sector Performance")
    sector_cols = st.columns(4)
    for idx, (name, data) in enumerate(st.session_state.sector_data.items()):
        with sector_cols[idx % 4]:
            color = "#00ff88" if data['performance'] > 0 else "#ff4444"
            st.markdown(f"<div class='sector-card'><div class='sector-name'>{name}</div><div class='sector-perf' style='color:{color};'>{data['performance']:+.1f}%</div><div style='font-size:11px;'>{data['signal']}</div></div>", unsafe_allow_html=True)

# ==================== AUTO-STREAM LOOP ====================
if st.session_state.auto_stream:
    time.sleep(30)
    st.rerun()

# ==================== INITIAL DATA LOAD ====================
if not st.session_state.exchange_data:
    update_all_data()

# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    AI Trading Dashboard - Auto-Broadcast to Twitter, YouTube, Facebook, Instagram, TikTok<br>
    <small>⚠️ Not financial advice. Always do your own research.</small>
</div>
""", unsafe_allow_html=True)
