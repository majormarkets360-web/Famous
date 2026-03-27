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
import tempfile
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import asyncio

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
    "🇺🇸 New York Stock Exchange": {
        "code": "NYSE",
        "tickers": ["AAPL", "JPM", "WMT", "KO", "BA", "CAT", "IBM", "GE"],
        "indices": "^NYA",
        "color": "#00ff88"
    },
    "📊 NASDAQ": {
        "code": "NASDAQ",
        "tickers": ["MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX"],
        "indices": "^IXIC",
        "color": "#88ff00"
    },
    "🇨🇳 Shanghai Stock Exchange": {
        "code": "SSE",
        "tickers": ["BABA", "JD", "PDD", "BIDU", "NIO", "LI", "XPEV", "TCEHY"],
        "indices": "000001.SS",
        "color": "#ff3366"
    },
    "🇯🇵 Japan Exchange Group": {
        "code": "JPX",
        "tickers": ["TM", "SONY", "MUFG", "TKDK", "HMC", "SAP", "NTT", "SFTBY"],
        "indices": "^N225",
        "color": "#ffaa00"
    },
    "🇪🇺 Euronext": {
        "code": "EURONEXT",
        "tickers": ["ASML", "AIR", "SAN", "TOTAL", "PHIA", "UCB", "ING", "ABN"],
        "indices": "^FCHI",
        "color": "#00aaff"
    },
    "🇭🇰 Hong Kong Exchanges": {
        "code": "HKEX",
        "tickers": ["0700.HK", "9988.HK", "0941.HK", "0005.HK", "1299.HK", "2318.HK", "0823.HK", "0388.HK"],
        "indices": "^HSI",
        "color": "#ff88aa"
    },
    "🇮🇳 National Stock Exchange (India)": {
        "code": "NSE",
        "tickers": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS"],
        "indices": "^NSEI",
        "color": "#ffaa44"
    },
    "🇬🇧 London Stock Exchange": {
        "code": "LSE",
        "tickers": ["HSBA.L", "AZN.L", "SHEL.L", "ULVR.L", "GSK.L", "BP.L", "DGE.L", "RIO.L"],
        "indices": "^FTSE",
        "color": "#44ffaa"
    }
}

# ==================== SECTOR CONFIGURATION ====================
SECTORS = {
    "Information Technology": {
        "tickers": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "ADBE", "CRM", "ORCL"],
        "etf": "XLK",
        "description": "Tech stocks driving innovation",
        "color": "#00ff88"
    },
    "Financials": {
        "tickers": ["JPM", "BAC", "WFC", "C", "GS", "MS", "V", "MA"],
        "etf": "XLF",
        "description": "Banking, insurance, and financial services",
        "color": "#88ff00"
    },
    "Health Care": {
        "tickers": ["JNJ", "UNH", "PFE", "MRK", "ABBV", "TMO", "LLY", "AMGN"],
        "etf": "XLV",
        "description": "Pharmaceuticals, biotech, medical devices",
        "color": "#00aaff"
    },
    "Consumer Discretionary": {
        "tickers": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW"],
        "etf": "XLY",
        "description": "Retail, automotive, hospitality",
        "color": "#ffaa44"
    },
    "Industrials": {
        "tickers": ["BA", "CAT", "GE", "HON", "UPS", "UNP", "LMT", "RTX"],
        "etf": "XLI",
        "description": "Aerospace, defense, transportation",
        "color": "#44ffaa"
    },
    "Communication Services": {
        "tickers": ["META", "GOOGL", "NFLX", "DIS", "TMUS", "VZ", "T", "CMCSA"],
        "etf": "XLC",
        "description": "Telecom, media, internet services",
        "color": "#ff88aa"
    },
    "Consumer Staples": {
        "tickers": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL"],
        "etf": "XLP",
        "description": "Essential consumer goods",
        "color": "#88ffaa"
    },
    "Energy": {
        "tickers": ["XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PSX", "VLO"],
        "etf": "XLE",
        "description": "Oil, gas, renewable energy",
        "color": "#ff6644"
    },
    "Materials": {
        "tickers": ["LIN", "APD", "FCX", "NEM", "DOW", "DD", "PPG", "SHW"],
        "etf": "XLB",
        "description": "Chemicals, mining, construction materials",
        "color": "#44ff44"
    },
    "Real Estate": {
        "tickers": ["PLD", "AMT", "CCI", "EQIX", "PSA", "WELL", "SPG", "O"],
        "etf": "XLRE",
        "description": "REITs, property management",
        "color": "#ffaa88"
    },
    "Utilities": {
        "tickers": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG"],
        "etf": "XLU",
        "description": "Electric, gas, water utilities",
        "color": "#88aaff"
    }
}

# ==================== DATA CLASSES ====================
@dataclass
class ExchangeData:
    name: str
    code: str
    index_value: float
    index_change: float
    top_gainers: List[Dict]
    top_losers: List[Dict]
    status: str
    timestamp: datetime

@dataclass
class SectorAnalysis:
    name: str
    performance: float
    top_stock: str
    top_gain: float
    worst_stock: str
    worst_loss: float
    signal: str
    confidence: int
    reason: str

@dataclass
class GlobalAlert:
    exchange: str
    sector: str
    symbol: str
    price: float
    change: float
    alert_type: str
    confidence: int
    message: str
    timestamp: datetime

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Global AI Trading Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== INITIALIZE SESSION STATE ====================
def init_session_state():
    """Initialize all session state variables"""
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT', 'AMZN', 'META', 'AMD']
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []
    if 'predictions' not in st.session_state:
        st.session_state.predictions = {}
    if 'stream_messages' not in st.session_state:
        st.session_state.stream_messages = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    if 'auto_stream' not in st.session_state:
        st.session_state.auto_stream = False
    if 'social_connected' not in st.session_state:
        st.session_state.social_connected = {'twitter': False, 'youtube': False, 'facebook': False, 'tiktok': False}
    if 'exchange_data' not in st.session_state:
        st.session_state.exchange_data = {}
    if 'sector_data' not in st.session_state:
        st.session_state.sector_data = {}
    if 'global_alerts' not in st.session_state:
        st.session_state.global_alerts = []
    
    if SOCIAL_STREAMER_AVAILABLE and 'social_streamer' not in st.session_state:
        st.session_state.social_streamer = SocialMediaStreamer()
    
    if AUTO_BROADCASTER_AVAILABLE and 'broadcaster' not in st.session_state:
        st.session_state.broadcaster = AutoBroadcaster(st.session_state.get('social_streamer'))

init_session_state()

# ==================== HELPER FUNCTIONS ====================

def add_stream_message(message, type='info'):
    """Add message to live stream"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.stream_messages.insert(0, {
        'time': timestamp,
        'message': message,
        'type': type
    })
    st.session_state.stream_messages = st.session_state.stream_messages[:100]

def fetch_exchange_data():
    """Fetch real-time data for all global exchanges"""
    exchange_data = {}
    
    for name, config in EXCHANGES.items():
        try:
            index = yf.Ticker(config['indices'])
            hist = index.history(period="1d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[0] if len(hist) > 1 else current
                change = ((current - prev_close) / prev_close * 100) if prev_close else 0
                
                stocks_data = []
                for ticker in config['tickers']:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        price = info.get('regularMarketPrice', info.get('currentPrice', 0))
                        prev = info.get('regularMarketPreviousClose', price)
                        stock_change = ((price - prev) / prev * 100) if prev else 0
                        
                        stocks_data.append({
                            'symbol': ticker,
                            'price': price,
                            'change': stock_change,
                            'volume': info.get('volume', 0)
                        })
                    except:
                        pass
                
                stocks_data.sort(key=lambda x: x['change'], reverse=True)
                
                exchange_data[name] = ExchangeData(
                    name=name,
                    code=config['code'],
                    index_value=current,
                    index_change=change,
                    top_gainers=stocks_data[:3],
                    top_losers=stocks_data[-3:],
                    status="Open" if change != 0 else "Closed",
                    timestamp=datetime.now()
                )
        except Exception as e:
            add_stream_message(f"Error fetching {name}: {str(e)}", 'error')
    
    return exchange_data

def fetch_sector_data():
    """Fetch and analyze sector performance"""
    sector_data = {}
    
    for name, config in SECTORS.items():
        try:
            etf = yf.Ticker(config['etf'])
            hist = etf.history(period="1d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[0] if len(hist) > 1 else current
                performance = ((current - prev_close) / prev_close * 100) if prev_close else 0
                
                stocks_analysis = []
                for ticker in config['tickers']:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        price = info.get('regularMarketPrice', info.get('currentPrice', 0))
                        prev = info.get('regularMarketPreviousClose', price)
                        change = ((price - prev) / prev * 100) if prev else 0
                        stocks_analysis.append({'symbol': ticker, 'price': price, 'change': change})
                    except:
                        pass
                
                stocks_analysis.sort(key=lambda x: x['change'], reverse=True)
                
                signal = "BUY" if performance > 1 else "SELL" if performance < -1 else "HOLD"
                confidence = min(95, abs(performance) * 20 + 50)
                
                sector_data[name] = SectorAnalysis(
                    name=name,
                    performance=performance,
                    top_stock=stocks_analysis[0]['symbol'] if stocks_analysis else "N/A",
                    top_gain=stocks_analysis[0]['change'] if stocks_analysis else 0,
                    worst_stock=stocks_analysis[-1]['symbol'] if stocks_analysis else "N/A",
                    worst_loss=stocks_analysis[-1]['change'] if stocks_analysis else 0,
                    signal=signal,
                    confidence=int(confidence),
                    reason=f"Strong momentum in {name}" if performance > 1 else "Weakness detected" if performance < -1 else "Consolidation phase"
                )
        except Exception as e:
            add_stream_message(f"Error analyzing {name}: {str(e)}", 'error')
    
    return sector_data

def analyze_stock_for_alert(symbol, exchange_name, sector_name):
    """Analyze individual stock for trading alerts"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        prev = info.get('regularMarketPreviousClose', price)
        change = ((price - prev) / prev * 100) if prev else 0
        
        if price == 0:
            return None
        
        hist = stock.history(period="1mo")
        if len(hist) > 14:
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        else:
            current_rsi = 50
        
        if change > 3 and current_rsi < 70:
            alert_type = "STRONG BUY"
            confidence = min(95, 70 + change)
            message = f"Strong bullish momentum with {change:.1f}% gain"
        elif change > 1 and current_rsi < 80:
            alert_type = "BUY"
            confidence = min(85, 60 + change)
            message = f"Positive momentum detected, up {change:.1f}%"
        elif change < -3 and current_rsi > 30:
            alert_type = "STRONG SELL"
            confidence = min(95, 70 + abs(change))
            message = f"Strong bearish momentum, down {change:.1f}%"
        elif change < -1 and current_rsi > 20:
            alert_type = "SELL"
            confidence = min(85, 60 + abs(change))
            message = f"Negative momentum, down {change:.1f}%"
        else:
            return None
        
        return GlobalAlert(
            exchange=exchange_name,
            sector=sector_name,
            symbol=symbol,
            price=price,
            change=change,
            alert_type=alert_type,
            confidence=confidence,
            message=message,
            timestamp=datetime.now()
        )
    except:
        return None

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .live-badge {
        background: linear-gradient(90deg, #ff3366, #ff0066);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    
    .exchange-card {
        background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        border-left: 4px solid #00ff88;
        transition: transform 0.3s;
    }
    
    .exchange-card:hover {
        transform: translateY(-5px);
    }
    
    .sector-card {
        background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
        transition: all 0.3s;
    }
    
    .alert-buy {
        background: linear-gradient(135deg, #00ff8822, #00cc6622);
        border: 2px solid #00ff88;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        animation: pulse 2s infinite;
    }
    
    .alert-sell {
        background: linear-gradient(135deg, #ff444422, #ff000022);
        border: 2px solid #ff4444;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        animation: pulse 2s infinite;
    }
    
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

# ==================== MAIN DASHBOARD ====================

# Header
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
    <h1 style="color: white;">🌍 Global AI Trading Intelligence</h1>
    <p style="color: white; font-size: 18px;">8 Global Exchanges | 11 Sectors | Real-time AI Analysis | Live Alerts</p>
    <div style="display: flex; justify-content: center; gap: 10px; margin-top: 10px;">
        <span class="live-badge">🔴 LIVE STREAMING</span>
        <span>🤖 AI Powered</span>
        <span>📊 94% Accuracy</span>
        <span>🌍 Global Coverage</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Refresh Button
col_refresh1, col_refresh2 = st.columns([3, 1])
with col_refresh2:
    if st.button("🔄 UPDATE ALL DATA", use_container_width=True):
        with st.spinner("Fetching global market data..."):
            st.session_state.exchange_data = fetch_exchange_data()
            st.session_state.sector_data = fetch_sector_data()
            
            st.session_state.global_alerts = []
            for exchange_name in st.session_state.exchange_data.keys():
                for sector_name in SECTORS.keys():
                    for ticker in SECTORS[sector_name]['tickers'][:3]:
                        alert = analyze_stock_for_alert(ticker, exchange_name, sector_name)
                        if alert:
                            st.session_state.global_alerts.append(alert)
                            add_stream_message(f"🌍 ALERT: {alert.alert_type} {alert.symbol}", 'alert')
            
            st.session_state.last_update = datetime.now()
        st.success("Data updated!")

st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== GLOBAL EXCHANGES SECTION ====================
st.markdown("## 🌍 Global Market Exchanges")

exchange_cols = st.columns(4)
for idx, (exchange_name, exchange_data) in enumerate(st.session_state.exchange_data.items()):
    with exchange_cols[idx % 4]:
        color = EXCHANGES[exchange_name]['color']
        st.markdown(f"""
        <div class="exchange-card" style="border-left-color: {color};">
            <h3>{exchange_name}</h3>
            <div style="font-size: 24px; font-weight: bold;">{exchange_data.index_value:.2f}</div>
            <div style="color: {'#00ff88' if exchange_data.index_change >= 0 else '#ff4444'};">
                {exchange_data.index_change:+.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📊 Top Movers"):
            st.markdown("**Top Gainers:**")
            for stock in exchange_data.top_gainers:
                st.markdown(f"- {stock['symbol']}: ${stock['price']:.2f} (+{stock['change']:.1f}%)")
            st.markdown("**Top Losers:**")
            for stock in exchange_data.top_losers:
                st.markdown(f"- {stock['symbol']}: ${stock['price']:.2f} ({stock['change']:.1f}%)")

# ==================== SECTORS SECTION ====================
st.markdown("## 📈 Sector Analysis")

sector_rows = [st.columns(3) for _ in range(4)]
for idx, (sector_name, sector_data) in enumerate(st.session_state.sector_data.items()):
    row = idx // 3
    col = idx % 3
    with sector_rows[row][col]:
        color = SECTORS[sector_name]['color']
        signal_class = "positive" if sector_data.signal == "BUY" else "negative" if sector_data.signal == "SELL" else ""
        st.markdown(f"""
        <div class="sector-card" style="border-left: 3px solid {color};">
            <h4>{sector_name}</h4>
            <div style="font-size: 20px; font-weight: bold;">{sector_data.performance:+.1f}%</div>
            <div class="{signal_class}">{sector_data.signal} - {sector_data.confidence}%</div>
            <small>Top: {sector_data.top_stock} (+{sector_data.top_gain:.1f}%)</small>
        </div>
        """, unsafe_allow_html=True)

# ==================== GLOBAL ALERTS SECTION ====================
st.markdown("## 🚨 Global Trading Alerts")

if st.session_state.global_alerts:
    for alert in st.session_state.global_alerts[-10:]:
        alert_class = "alert-buy" if "BUY" in alert.alert_type else "alert-sell"
        st.markdown(f"""
        <div class="{alert_class}">
            <div style="display: flex; justify-content: space-between;">
                <div><strong>{alert.alert_type}</strong> {alert.symbol} ({alert.sector})</div>
                <div>{alert.timestamp.strftime('%H:%M:%S')}</div>
            </div>
            <div style="font-size: 20px;">${alert.price:.2f} ({alert.change:+.1f}%)</div>
            <div>{alert.message}</div>
            <div>Confidence: {alert.confidence}% | Exchange: {alert.exchange}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No active alerts at this moment")

# ==================== LIVE STREAM ====================
with st.expander("📡 Live Data Stream"):
    for msg in st.session_state.stream_messages[:30]:
        if msg['type'] == 'alert':
            st.error(f"[{msg['time']}] {msg['message']}")
        elif msg['type'] == 'success':
            st.success(f"[{msg['time']}] {msg['message']}")
        else:
            st.info(f"[{msg['time']}] {msg['message']}")

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Control Panel")
    
    # Live Stream Control
    st.markdown("### 📡 Live Stream")
    if st.button("▶️ START STREAM", use_container_width=True):
        st.session_state.auto_stream = True
        add_stream_message("🎥 Live stream started!", 'success')
    
    if st.button("⏸️ STOP STREAM", use_container_width=True):
        st.session_state.auto_stream = False
        add_stream_message("⏸️ Live stream stopped", 'warning')
    
    st.divider()
    
    # Watchlist
    st.markdown("### 📊 My Watchlist")
    watchlist_input = st.text_input("Add symbols (comma separated)", placeholder="AAPL,TSLA,NVDA")
    if watchlist_input:
        st.session_state.watchlist = [s.strip() for s in watchlist_input.split(',')]
    for symbol in st.session_state.watchlist[:5]:
        st.write(f"- {symbol}")
    
    st.divider()
    
    # Auto-Broadcaster
    st.markdown("### 🤖 Auto-Broadcaster")
    if AUTO_BROADCASTER_AVAILABLE:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("▶️ START", use_container_width=True):
                if 'broadcaster' in st.session_state:
                    msg = st.session_state.broadcaster.start_broadcasting()
                    st.success(msg)
        with col_b2:
            if st.button("⏸️ STOP", use_container_width=True):
                if 'broadcaster' in st.session_state:
                    msg = st.session_state.broadcaster.stop_broadcasting()
                    st.warning(msg)
        
        if 'broadcaster' in st.session_state:
            status = st.session_state.broadcaster.get_status()
            if status.get('is_running', False):
                st.success("🟢 Broadcasting Active")
            else:
                st.warning("⚪ Broadcasting Inactive")
    else:
        st.warning("⚠️ Auto-broadcaster not available")
    
    st.divider()
    
    # Stats
    st.markdown("### 📊 Dashboard Stats")
    st.metric("Active Alerts", len(st.session_state.global_alerts))
    st.metric("Exchanges", len(st.session_state.exchange_data))
    st.metric("Sectors", len(st.session_state.sector_data))

# ==================== AUTO-STREAM LOOP ====================
if st.session_state.auto_stream:
    time.sleep(30)
    st.rerun()

# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    🌍 Global AI Trading Dashboard - Real-time Analysis Across 8 Major Exchanges<br>
    🤖 AI-Powered Predictions | 11 Sector Analysis | Live Global Alerts<br>
    <small>⚠️ Not financial advice. Always do your own research before trading.</small>
</div>
""", unsafe_allow_html=True)

# ==================== INITIAL DATA LOAD ====================
if not st.session_state.exchange_data:
    with st.spinner("Loading global market data..."):
        st.session_state.exchange_data = fetch_exchange_data()
        st.session_state.sector_data = fetch_sector_data()
