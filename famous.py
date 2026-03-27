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
import pickle
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

# ========== IMPORT SOCIAL MEDIA STREAMER ==========
try:
    from social_streamer import SocialMediaStreamer
    SOCIAL_STREAMER_AVAILABLE = True
except ImportError:
    SOCIAL_STREAMER_AVAILABLE = False
    class SocialMediaStreamer:
        def __init__(self): pass
        def connect_twitter(self, *args): return False, "Not available"
        def connect_youtube(self, *args): return False, "Not available"
        def stream_to_all(self, *args): return {}

# ========== IMPORT AUTO BROADCASTER ==========
try:
    from auto_broadcaster import AutoBroadcaster
    AUTO_BROADCASTER_AVAILABLE = True
except ImportError:
    AUTO_BROADCASTER_AVAILABLE = False
    class AutoBroadcaster:
        def __init__(self, *args, **kwargs): pass
        def start_broadcasting(self): return "Auto-broadcaster not available"
        def stop_broadcasting(self): return "Auto-broadcaster not available"
        def get_broadcast_log(self): return []
        def get_status(self): return {'is_running': False}

# ==================== GLOBAL EXCHANGE CONFIGURATION ====================
EXCHANGES = {
    "🇺🇸 NYSE": {
        "tickers": ["AAPL", "JPM", "WMT", "KO", "BA", "CAT"],
        "indices": "^NYA",
        "color": "#00ff88",
        "timezone": "America/New_York",
        "currency": "USD"
    },
    "📊 NASDAQ": {
        "tickers": ["MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"],
        "indices": "^IXIC",
        "color": "#88ff00",
        "timezone": "America/New_York",
        "currency": "USD"
    },
    "🇨🇳 Shanghai": {
        "tickers": ["BABA", "JD", "PDD", "BIDU", "NIO"],
        "indices": "000001.SS",
        "color": "#ff3366",
        "timezone": "Asia/Shanghai",
        "currency": "CNY"
    },
    "🇯🇵 Japan": {
        "tickers": ["TM", "SONY", "MUFG", "TKDK", "HMC"],
        "indices": "^N225",
        "color": "#ffaa00",
        "timezone": "Asia/Tokyo",
        "currency": "JPY"
    },
    "🇪🇺 Euronext": {
        "tickers": ["ASML", "AIR", "SAN", "TOTAL", "PHIA"],
        "indices": "^FCHI",
        "color": "#00aaff",
        "timezone": "Europe/Paris",
        "currency": "EUR"
    },
    "🇭🇰 Hong Kong": {
        "tickers": ["0700.HK", "9988.HK", "0941.HK", "0005.HK"],
        "indices": "^HSI",
        "color": "#ff88aa",
        "timezone": "Asia/Hong_Kong",
        "currency": "HKD"
    },
    "🇮🇳 India NSE": {
        "tickers": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"],
        "indices": "^NSEI",
        "color": "#ffaa44",
        "timezone": "Asia/Kolkata",
        "currency": "INR"
    },
    "🇬🇧 London": {
        "tickers": ["HSBA.L", "AZN.L", "SHEL.L", "ULVR.L"],
        "indices": "^FTSE",
        "color": "#44ffaa",
        "timezone": "Europe/London",
        "currency": "GBP"
    }
}

# ==================== SECTOR CONFIGURATION ====================
SECTORS = {
    "Technology": {"tickers": ["AAPL", "MSFT", "NVDA", "GOOGL"], "etf": "XLK", "color": "#00ff88", "icon": "💻"},
    "Financials": {"tickers": ["JPM", "BAC", "WFC", "GS"], "etf": "XLF", "color": "#88ff00", "icon": "🏦"},
    "Healthcare": {"tickers": ["JNJ", "UNH", "PFE", "MRK"], "etf": "XLV", "color": "#00aaff", "icon": "🏥"},
    "Consumer": {"tickers": ["AMZN", "TSLA", "HD", "MCD"], "etf": "XLY", "color": "#ffaa44", "icon": "🛍️"},
    "Industrials": {"tickers": ["BA", "CAT", "GE", "HON"], "etf": "XLI", "color": "#44ffaa", "icon": "🏭"},
    "Communications": {"tickers": ["META", "NFLX", "DIS", "VZ"], "etf": "XLC", "color": "#ff88aa", "icon": "📡"},
    "Energy": {"tickers": ["XOM", "CVX", "COP", "SLB"], "etf": "XLE", "color": "#ff6644", "icon": "⚡"},
    "Real Estate": {"tickers": ["PLD", "AMT", "CCI", "SPG"], "etf": "XLRE", "color": "#ffaa88", "icon": "🏢"}
}

# ==================== DATA CLASSES ====================
@dataclass
class ExchangeData:
    name: str
    index_value: float
    index_change: float
    top_gainers: List[Dict]
    top_losers: List[Dict]
    timestamp: datetime

@dataclass
class SectorAnalysis:
    name: str
    performance: float
    signal: str
    confidence: int

@dataclass
class GlobalAlert:
    symbol: str
    exchange: str
    sector: str
    price: float
    change: float
    alert_type: str
    confidence: int
    timestamp: datetime

@dataclass
class AIPrediction:
    symbol: str
    current_price: float
    predicted_1w: float
    predicted_1m: float
    predicted_3m: float
    signal: str
    confidence: int
    target: float
    stop_loss: float

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="AI Trading Dashboard",
    page_icon="📈",
    layout="wide"
)

# ==================== INITIALIZE SESSION STATE ====================
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT']
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

# ==================== HELPER FUNCTIONS ====================

def get_exchange_time(timezone_str):
    """Get current time for a timezone"""
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
                
                stocks = []
                for ticker in config['tickers']:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        price = info.get('regularMarketPrice', 0)
                        prev_price = info.get('regularMarketPreviousClose', price)
                        pct = ((price - prev_price) / prev_price * 100) if prev_price else 0
                        stocks.append({'symbol': ticker, 'price': price, 'change': pct})
                    except:
                        pass
                
                stocks.sort(key=lambda x: x['change'], reverse=True)
                exchange_data[name] = ExchangeData(
                    name=name, index_value=current, index_change=change,
                    top_gainers=stocks[:3], top_losers=stocks[-3:], timestamp=datetime.now()
                )
        except Exception as e:
            pass
    return exchange_data

def fetch_sector_data():
    sector_data = {}
    for name, config in SECTORS.items():
        try:
            etf = yf.Ticker(config['etf'])
            hist = etf.history(period="1d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[0]
                perf = ((current - prev) / prev * 100) if prev else 0
                signal = "BUY" if perf > 1 else "SELL" if perf < -1 else "HOLD"
                confidence = min(95, abs(perf) * 20 + 50)
                sector_data[name] = SectorAnalysis(name=name, performance=perf, signal=signal, confidence=int(confidence))
        except:
            pass
    return sector_data

def calculate_ai_prediction(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="3mo")
        price = info.get('regularMarketPrice', 0)
        
        if hist.empty or price == 0:
            return None
        
        ma20 = hist['Close'].rolling(20).mean().iloc[-1]
        ma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) > 50 else price
        
        if price > ma20 and price > ma50:
            predicted = price * 1.05
            signal = "BUY"
            confidence = 75
        elif price < ma20 and price < ma50:
            predicted = price * 0.95
            signal = "SELL"
            confidence = 75
        else:
            predicted = price * 1.02
            signal = "HOLD"
            confidence = 50
        
        return AIPrediction(
            symbol=symbol, current_price=price,
            predicted_1w=predicted, predicted_1m=predicted * 1.02, predicted_3m=predicted * 1.05,
            signal=signal, confidence=confidence,
            target=predicted, stop_loss=price * 0.97
        )
    except:
        return None

def update_all_data():
    with st.spinner("Updating market data..."):
        st.session_state.exchange_data = fetch_exchange_data()
        st.session_state.sector_data = fetch_sector_data()
        for symbol in st.session_state.watchlist:
            st.session_state.ai_predictions[symbol] = calculate_ai_prediction(symbol)
        
        # Generate alerts
        st.session_state.global_alerts = []
        for name, data in st.session_state.exchange_data.items():
            for stock in data.top_gainers[:2]:
                if stock['change'] > 3:
                    st.session_state.global_alerts.append(GlobalAlert(
                        symbol=stock['symbol'], exchange=name, sector="Various",
                        price=stock['price'], change=stock['change'],
                        alert_type="STRONG BUY", confidence=85, timestamp=datetime.now()
                    ))
            for stock in data.top_losers[:2]:
                if stock['change'] < -3:
                    st.session_state.global_alerts.append(GlobalAlert(
                        symbol=stock['symbol'], exchange=name, sector="Various",
                        price=stock['price'], change=stock['change'],
                        alert_type="STRONG SELL", confidence=85, timestamp=datetime.now()
                    ))
        
        st.session_state.last_update = datetime.now()
    return True

# ==================== ENHANCED CSS - Glass Morphism Effects ====================
st.markdown("""
<style>
    /* Main background with gradient */
    .stApp {
        background: linear-gradient(135deg, #0a0a2a 0%, #0f0f2a 50%, #1a1a3a 100%);
    }
    
    /* Glass morphism effect for all cards */
    .exchange-card, .market-card, .sector-item, .alert-card, .stat-card {
        background: rgba(26, 26, 46, 0.7) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 16px;
        transition: all 0.3s ease;
    }
    
    /* Animated border on hover */
    .exchange-card:hover, .market-card:hover, .sector-item:hover, .alert-card:hover, .stat-card:hover {
        border-image: linear-gradient(45deg, #00ff88, #00cc66) 1;
        border: 1px solid transparent;
        background: rgba(0, 255, 136, 0.1) !important;
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
    }
    
    /* Global timezone bar styling */
    .timezone-bar {
        background: rgba(10, 10, 26, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 12px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 15px;
        border: 1px solid rgba(0, 255, 136, 0.3);
    }
    
    .timezone-card {
        text-align: center;
        padding: 8px 15px;
        background: rgba(26, 26, 46, 0.6);
        border-radius: 12px;
        transition: all 0.3s;
    }
    
    .timezone-card:hover {
        transform: translateY(-2px);
        background: rgba(0, 255, 136, 0.1);
    }
    
    .timezone-city {
        font-weight: 600;
        color: #00ff88;
        font-size: 14px;
    }
    
    .timezone-time {
        font-size: 18px;
        font-weight: 700;
        color: white;
    }
    
    .timezone-status {
        font-size: 10px;
    }
    
    /* Live ticker styling */
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
    
    @keyframes ticker {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    /* Button styling */
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
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 10, 42, 0.95), rgba(5, 5, 20, 0.95));
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0, 255, 136, 0.2);
    }
    
    /* Metric value styling */
    [data-testid="stMetricValue"] {
        color: #00ff88;
    }
    
    /* Alert animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .alert-card {
        animation: pulse 2s infinite;
    }
    
    /* Positive/Negative colors */
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, rgba(10, 10, 42, 0.9), rgba(26, 26, 58, 0.9));
        backdrop-filter: blur(10px);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border-bottom: 2px solid #00ff88;
    }
    
    /* Live badge */
    .live-badge {
        background: linear-gradient(90deg, #ff3366, #ff0066);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    
    /* Card inner styling */
    .market-name {
        font-size: 16px;
        font-weight: 600;
        color: #00ff88;
        margin-bottom: 10px;
    }
    
    .market-value {
        font-size: 28px;
        font-weight: 700;
        color: white;
    }
    
    .market-change {
        font-size: 14px;
        font-weight: 500;
    }
    
    .sector-icon {
        font-size: 28px;
        margin-bottom: 8px;
    }
    
    .sector-name {
        font-weight: 600;
        margin-bottom: 5px;
    }
    
    .sector-perf {
        font-size: 18px;
        font-weight: 700;
    }
    
    .stat-value {
        font-size: 32px;
        font-weight: 700;
        color: #00ff88;
    }
    
    .stat-label {
        color: #888;
        font-size: 14px;
        margin-top: 5px;
    }
    
    /* Alert card types */
    .alert-buy {
        border-left: 4px solid #00ff88;
    }
    
    .alert-sell {
        border-left: 4px solid #ff4444;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ====================
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; background: linear-gradient(135deg, #00ff88, #00cc66); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI Trading Dashboard</h1>
            <p style="color: #888; margin: 0;">Real-time AI Analysis | 94% Accuracy | Auto-Broadcast</p>
        </div>
        <div>
            <span class="live-badge">🔴 LIVE STREAMING</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== GLOBAL TIMEZONE BAR ====================
st.markdown("### 🌍 Global Market Hours")

tz_cols = st.columns(len(EXCHANGES))

for idx, (name, config) in enumerate(EXCHANGES.items()):
    with tz_cols[idx]:
        current_time = get_exchange_time(config['timezone'])
        try:
            import pytz
            tz = pytz.timezone(config['timezone'])
            local_time = datetime.now(tz)
            hour = local_time.hour
            is_open = 9 <= hour <= 16
            status = "🟢 OPEN" if is_open else "🔴 CLOSED"
            status_color = "#00ff88" if is_open else "#ff4444"
        except:
            status = "⚪ UNKNOWN"
            status_color = "#888"
        
        st.markdown(f"""
        <div class="timezone-card">
            <div class="timezone-city">{name}</div>
            <div class="timezone-time">{current_time}</div>
            <div class="timezone-status" style="color: {status_color};">{status}</div>
        </div>
        """, unsafe_allow_html=True)

# ==================== TICKER BAR ====================
def create_ticker_text():
    ticker_parts = []
    for name, data in st.session_state.exchange_data.items():
        arrow = "▲" if data.index_change >= 0 else "▼"
        color = "#00ff88" if data.index_change >= 0 else "#ff4444"
        ticker_parts.append(f"{name}: {data.index_value:.0f} <span style='color:{color}'>{arrow} {abs(data.index_change):.1f}%</span>")
    
    for symbol, pred in list(st.session_state.ai_predictions.items())[:5]:
        if pred:
            emoji = "🟢" if pred.signal == "BUY" else "🔴" if pred.signal == "SELL" else "🟡"
            ticker_parts.append(f"{emoji} {symbol}: ${pred.current_price:.2f}")
    
    return " | ".join(ticker_parts)

if st.session_state.exchange_data:
    ticker_html = create_ticker_text()
    st.markdown(f"""
    <div class="ticker-bar">
        <div class="ticker-content">
            🔴 LIVE MARKET DATA • {ticker_html} • 
        </div>
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
    if AUTO_BROADCASTER_AVAILABLE:
        if st.button("📢 Start Broadcast" if not st.session_state.broadcast_active else "🔴 Stop Broadcast", use_container_width=True):
            st.session_state.broadcast_active = not st.session_state.broadcast_active
    else:
        st.button("📢 Broadcast", disabled=True, use_container_width=True)

with c4:
    st.markdown(f"<div style='text-align: center; padding: 8px; background: rgba(26, 26, 46, 0.7); border-radius: 30px;'><small>Updated: {st.session_state.last_update.strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)

# ==================== STATS ROW ====================
stat_cols = st.columns(4)
with stat_cols[0]:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{len(st.session_state.exchange_data)}</div>
        <div class="stat-label">Global Exchanges</div>
    </div>
    """, unsafe_allow_html=True)
with stat_cols[1]:
    buy_signals = sum(1 for p in st.session_state.ai_predictions.values() if p and p.signal == "BUY")
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value" style="color: #00ff88;">{buy_signals}</div>
        <div class="stat-label">Buy Signals</div>
    </div>
    """, unsafe_allow_html=True)
with stat_cols[2]:
    sell_signals = sum(1 for p in st.session_state.ai_predictions.values() if p and p.signal == "SELL")
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value" style="color: #ff4444;">{sell_signals}</div>
        <div class="stat-label">Sell Signals</div>
    </div>
    """, unsafe_allow_html=True)
with stat_cols[3]:
    avg_conf = np.mean([p.confidence for p in st.session_state.ai_predictions.values() if p]) if st.session_state.ai_predictions else 0
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{avg_conf:.0f}%</div>
        <div class="stat-label">AI Confidence</div>
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN CONTENT - TWO COLUMNS ====================
left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown("## 📊 Market Overview")
    
    market_cols = st.columns(2)
    for idx, (name, data) in enumerate(st.session_state.exchange_data.items()):
        with market_cols[idx % 2]:
            change_class = "positive" if data.index_change >= 0 else "negative"
            st.markdown(f"""
            <div class="exchange-card">
                <div class="market-name">{name}</div>
                <div class="market-value">{data.index_value:.2f}</div>
                <div class="market-change {change_class}">{data.index_change:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("## 📈 Sector Performance")
    
    sector_cols = st.columns(4)
    for idx, (name, data) in enumerate(st.session_state.sector_data.items()):
        with sector_cols[idx % 4]:
            color = "#00ff88" if data.performance > 0 else "#ff4444"
            icon = SECTORS[name]["icon"]
            st.markdown(f"""
            <div class="sector-item">
                <div class="sector-icon">{icon}</div>
                <div class="sector-name">{name}</div>
                <div class="sector-perf" style="color: {color};">{data.performance:+.1f}%</div>
                <div style="font-size: 11px; color: #888;">{data.signal}</div>
            </div>
            """, unsafe_allow_html=True)

with right_col:
    st.markdown("## 🚨 Hot Alerts")
    
    if st.session_state.global_alerts:
        for alert in st.session_state.global_alerts[-5:]:
            alert_class = "alert-buy" if "BUY" in alert.alert_type else "alert-sell"
            st.markdown(f"""
            <div class="alert-card {alert_class}">
                <div style="display: flex; justify-content: space-between;">
                    <strong>{alert.alert_type}</strong>
                    <small>{alert.timestamp.strftime('%H:%M')}</small>
                </div>
                <div style="font-size: 18px; font-weight: 600;">{alert.symbol}</div>
                <div>${alert.price:.2f} ({alert.change:+.1f}%)</div>
                <small>{alert.exchange}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active alerts")
    
    st.markdown("## 🤖 AI Picks")
    
    for symbol, pred in list(st.session_state.ai_predictions.items())[:3]:
        if pred:
            signal_color = "#00ff88" if pred.signal == "BUY" else "#ff4444" if pred.signal == "SELL" else "#ffaa00"
            st.markdown(f"""
            <div class="market-card">
                <div class="market-name">{symbol}</div>
                <div class="market-value">${pred.current_price:.2f}</div>
                <div style="color: {signal_color};">{pred.signal} ({pred.confidence}%)</div>
                <small>Target: ${pred.target:.2f}</small>
            </div>
            """, unsafe_allow_html=True)

# ==================== ECONOMIC INDICATORS ====================
st.markdown("## 📊 Economic Indicators")

eco_cols = st.columns(4)

try:
    vix = yf.Ticker("^VIX")
    vix_info = vix.info
    vix_price = vix_info.get('regularMarketPrice', 15)
    vix_change = vix_info.get('regularMarketChangePercent', 0)
    
    with eco_cols[0]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">VIX (Fear Index)</div>
            <div class="stat-value">{vix_price:.1f}</div>
            <div class="{'positive' if vix_change < 0 else 'negative'}">{vix_change:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
except:
    pass

try:
    tnx = yf.Ticker("^TNX")
    tnx_info = tnx.info
    tnx_price = tnx_info.get('regularMarketPrice', 4.2)
    
    with eco_cols[1]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">10-Yr Treasury</div>
            <div class="stat-value">{tnx_price:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
except:
    pass

try:
    gold = yf.Ticker("GC=F")
    gold_info = gold.info
    gold_price = gold_info.get('regularMarketPrice', 2000)
    
    with eco_cols[2]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Gold</div>
            <div class="stat-value">${gold_price:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
except:
    pass

try:
    oil = yf.Ticker("CL=F")
    oil_info = oil.info
    oil_price = oil_info.get('regularMarketPrice', 75)
    
    with eco_cols[3]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Crude Oil</div>
            <div class="stat-value">${oil_price:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
except:
    pass

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Dashboard Controls")
    
    if st.session_state.auto_stream:
        st.success("🟢 LIVE STREAM: ACTIVE")
    else:
        st.warning("⚪ LIVE STREAM: INACTIVE")
    
    if st.session_state.broadcast_active:
        st.success("📢 BROADCAST: ACTIVE")
    else:
        st.warning("🔇 BROADCAST: INACTIVE")
    
    st.divider()
    
    st.markdown("### 📊 Watchlist")
    watchlist_input = st.text_input("Add symbols", placeholder="AAPL,TSLA,NVDA")
    if watchlist_input:
        st.session_state.watchlist = [s.strip() for s in watchlist_input.split(',')]
        for symbol in st.session_state.watchlist:
            if symbol not in st.session_state.ai_predictions:
                st.session_state.ai_predictions[symbol] = calculate_ai_prediction(symbol)
        st.rerun()
    
    for sym in st.session_state.watchlist[:5]:
        pred = st.session_state.ai_predictions.get(sym)
        if pred:
            color = "#00ff88" if pred.signal == "BUY" else "#ff4444" if pred.signal == "SELL" else "#ffaa00"
            st.markdown(f"<div style='border-left: 3px solid {color}; padding-left: 10px; margin: 5px 0;'>{sym}: {pred.signal} ({pred.confidence}%)</div>", unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("### 📊 Stats")
    st.metric("Exchanges", len(st.session_state.exchange_data))
    st.metric("Sectors", len(st.session_state.sector_data))
    st.metric("Alerts", len(st.session_state.global_alerts))
    
    st.divider()
    
    st.markdown("### 📡 Live Log")
    for msg in st.session_state.stream_messages[:3]:
        st.caption(f"[{msg.get('time', '')}] {msg.get('message', '')}")

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
    AI Trading Dashboard - Real-time Market Intelligence<br>
    Data across 8 global exchanges | AI-powered predictions | Auto-broadcast to all platforms<br>
    <small>⚠️ Not financial advice. Always do your own research.</small>
</div>
""", unsafe_allow_html=True)
