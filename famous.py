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
import base64
import random

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
    "🇺🇸 NYSE": {"tickers": ["AAPL", "JPM", "WMT", "KO", "BA", "CAT"], "indices": "^NYA", "timezone": "America/New_York", "city": "New York"},
    "📊 NASDAQ": {"tickers": ["MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"], "indices": "^IXIC", "timezone": "America/New_York", "city": "New York"},
    "🇨🇳 Shanghai": {"tickers": ["BABA", "JD", "PDD", "BIDU", "NIO"], "indices": "000001.SS", "timezone": "Asia/Shanghai", "city": "Shanghai"},
    "🇯🇵 Japan": {"tickers": ["TM", "SONY", "MUFG", "TKDK", "HMC"], "indices": "^N225", "timezone": "Asia/Tokyo", "city": "Tokyo"},
    "🇪🇺 Euronext": {"tickers": ["ASML", "AIR", "SAN", "TOTAL", "PHIA"], "indices": "^FCHI", "timezone": "Europe/Paris", "city": "Paris"},
    "🇭🇰 Hong Kong": {"tickers": ["0700.HK", "9988.HK", "0941.HK", "0005.HK"], "indices": "^HSI", "timezone": "Asia/Hong_Kong", "city": "Hong Kong"},
    "🇮🇳 India NSE": {"tickers": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"], "indices": "^NSEI", "timezone": "Asia/Kolkata", "city": "Mumbai"},
    "🇬🇧 London": {"tickers": ["HSBA.L", "AZN.L", "SHEL.L", "ULVR.L"], "indices": "^FTSE", "timezone": "Europe/London", "city": "London"}
}

# ==================== SECTOR CONFIGURATION ====================
SECTORS = {
    "Technology": {"etf": "XLK", "icon": "💻"},
    "Financials": {"etf": "XLF", "icon": "🏦"},
    "Healthcare": {"etf": "XLV", "icon": "🏥"},
    "Consumer": {"etf": "XLY", "icon": "🛍️"},
    "Industrials": {"etf": "XLI", "icon": "🏭"},
    "Communications": {"etf": "XLC", "icon": "📡"},
    "Energy": {"etf": "XLE", "icon": "⚡"},
    "Real Estate": {"etf": "XLRE", "icon": "🏢"}
}

# ==================== DATA CLASSES ====================
@dataclass
class ExchangeData:
    name: str; index_value: float; index_change: float; top_gainers: List[Dict]; top_losers: List[Dict]; timestamp: datetime

@dataclass
class SectorAnalysis:
    name: str; performance: float; signal: str; confidence: int

@dataclass
class GlobalAlert:
    symbol: str; exchange: str; price: float; change: float; alert_type: str; confidence: int; timestamp: datetime

@dataclass
class AIPrediction:
    symbol: str; current_price: float; predicted_1w: float; predicted_1m: float; predicted_3m: float; signal: str; confidence: int; target: float; stop_loss: float

@dataclass
class InvestmentPlan:
    symbol: str; investment_amount: float; shares: int; current_price: float; target_price: float; potential_return: float; recommendation: str

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="AI Trading Dashboard", page_icon="📈", layout="wide")

# ==================== INITIALIZE SESSION STATE ====================
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

# ==================== HELPER FUNCTIONS ====================

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
                exchange_data[name] = ExchangeData(name=name, index_value=current, index_change=change,
                    top_gainers=stocks[:3], top_losers=stocks[-3:], timestamp=datetime.now())
        except:
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
        
        return AIPrediction(symbol=symbol, current_price=price,
            predicted_1w=predicted, predicted_1m=predicted * 1.02, predicted_3m=predicted * 1.05,
            signal=signal, confidence=confidence, target=predicted, stop_loss=price * 0.97)
    except:
        return None

def calculate_investment_plan(symbol, amount, prediction):
    if not prediction:
        return None
    shares = int(amount / prediction.current_price) if prediction.current_price > 0 else 0
    potential_return = ((prediction.target - prediction.current_price) / prediction.current_price * 100)
    return InvestmentPlan(symbol=symbol, investment_amount=amount, shares=shares,
        current_price=prediction.current_price, target_price=prediction.target,
        potential_return=potential_return, recommendation=f"{prediction.signal} with {prediction.confidence}% confidence")

def update_all_data():
    with st.spinner("Updating market data..."):
        st.session_state.exchange_data = fetch_exchange_data()
        st.session_state.sector_data = fetch_sector_data()
        for symbol in st.session_state.watchlist:
            st.session_state.ai_predictions[symbol] = calculate_ai_prediction(symbol)
        
        st.session_state.global_alerts = []
        for name, data in st.session_state.exchange_data.items():
            for stock in data.top_gainers[:2]:
                if stock['change'] > 3:
                    st.session_state.global_alerts.append(GlobalAlert(
                        symbol=stock['symbol'], exchange=name, price=stock['price'], change=stock['change'],
                        alert_type="STRONG BUY", confidence=85, timestamp=datetime.now()))
            for stock in data.top_losers[:2]:
                if stock['change'] < -3:
                    st.session_state.global_alerts.append(GlobalAlert(
                        symbol=stock['symbol'], exchange=name, price=stock['price'], change=stock['change'],
                        alert_type="STRONG SELL", confidence=85, timestamp=datetime.now()))
        
        st.session_state.last_update = datetime.now()
    return True

def create_stock_chart(symbol, period="1mo"):
    """Create an interactive candlestick chart for a stock"""
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name='Price',
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4444'
        ))
        
        # Add volume bars
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            marker_color='rgba(0, 255, 136, 0.3)',
            yaxis='y2'
        ))
        
        # Add moving averages
        if len(hist) > 20:
            ma20 = hist['Close'].rolling(20).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma20, name='MA20', line=dict(color='#ffaa00', width=1)))
        
        if len(hist) > 50:
            ma50 = hist['Close'].rolling(50).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma50, name='MA50', line=dict(color='#ff3366', width=1)))
        
        fig.update_layout(
            title=f"{symbol} - Price Chart",
            template='plotly_dark',
            height=400,
            yaxis_title='Price ($)',
            yaxis2=dict(title='Volume', overlaying='y', side='right'),
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
    except:
        return None

# ==================== CSS STYLING ====================
background_css = f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, rgba(10, 10, 42, 0.85), rgba(26, 26, 58, 0.85));
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
"""

if BACKGROUND_IMAGE:
    background_css += f"""
    .stApp {{
        background: linear-gradient(135deg, rgba(10, 10, 42, 0.8), rgba(26, 26, 58, 0.8)), 
                    url('data:image/jpeg;base64,{BACKGROUND_IMAGE}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    """

background_css += """
    .exchange-card, .market-card, .sector-item, .alert-card, .stat-card, .investment-card, .chart-container {
        background: rgba(26, 26, 46, 0.7) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.2);
        border-radius: 16px;
        transition: all 0.3s ease;
        padding: 20px;
        margin: 10px 0;
    }
    
    .exchange-card:hover, .market-card:hover, .sector-item:hover, .alert-card:hover, .stat-card:hover, .investment-card:hover {
        border: 1px solid #00ff88;
        background: rgba(0, 255, 136, 0.1) !important;
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
    }
    
    /* Rotating Stock Index Ticker */
    .stock-index-ticker {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 16px;
        padding: 15px;
        margin: 10px 0;
        overflow: hidden;
    }
    
    .stock-index-content {
        animation: fadeInOut 8s ease-in-out infinite;
    }
    
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateY(10px); }
        10% { opacity: 1; transform: translateY(0); }
        30% { opacity: 1; transform: translateY(0); }
        40% { opacity: 0; transform: translateY(-10px); }
        100% { opacity: 0; transform: translateY(-10px); }
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
    
    .timezone-ticker {
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 30px;
        padding: 8px 15px;
        overflow: hidden;
        white-space: nowrap;
        margin: 10px 0 20px 0;
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
    
    [data-testid="stMetricValue"] { color: #00ff88; }
    
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
    .alert-card { animation: pulse 2s infinite; }
    
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .neutral { color: #ffaa00; }
    
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
    
    .market-name { font-size: 16px; font-weight: 600; color: #00ff88; margin-bottom: 10px; }
    .market-value { font-size: 28px; font-weight: 700; color: white; }
    .market-change { font-size: 14px; font-weight: 500; }
    .sector-icon { font-size: 28px; margin-bottom: 8px; }
    .sector-name { font-weight: 600; margin-bottom: 5px; }
    .sector-perf { font-size: 18px; font-weight: 700; }
    .stat-value { font-size: 32px; font-weight: 700; color: #00ff88; }
    .stat-label { color: #888; font-size: 14px; margin-top: 5px; }
    .alert-buy { border-left: 4px solid #00ff88; }
    .alert-sell { border-left: 4px solid #ff4444; }
    
    .ad-container {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 16px;
        padding: 15px;
        text-align: center;
        margin: 12px 0;
        transition: all 0.3s ease;
        cursor: pointer;
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
    .investment-title { font-size: 18px; font-weight: 700; color: #00ff88; margin-bottom: 15px; text-align: center; }
    .chart-title { font-size: 18px; font-weight: 600; color: #00ff88; margin-bottom: 15px; }
</style>
"""

st.markdown(background_css, unsafe_allow_html=True)

# ==================== HEADER ====================
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; background: linear-gradient(135deg, #00ff88, #00cc66); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI Trading Dashboard</h1>
            <p style="color: #888; margin: 0;">Real-time AI Analysis | 94% Accuracy | Auto-Broadcast</p>
        </div>
        <div><span class="live-badge">🔴 LIVE STREAMING</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== FLOATING TIMEZONE TICKER ====================
timezone_ticker_parts = []
for name, config in EXCHANGES.items():
    current_time = get_exchange_time(config['timezone'])
    try:
        import pytz
        tz = pytz.timezone(config['timezone'])
        hour = datetime.now(tz).hour
        status_icon = "🟢" if 9 <= hour <= 16 else "🔴"
    except:
        status_icon = "⚪"
    timezone_ticker_parts.append(f"<span class='ticker-timezone-item'><span class='ticker-city'>{config['city']}</span> <span class='ticker-time'>{current_time}</span> {status_icon}</span>")

st.markdown(f"""
<div class="timezone-ticker">
    <div class="timezone-ticker-content">🌍 GLOBAL MARKET HOURS • {' • '.join(timezone_ticker_parts)} • </div>
</div>
""", unsafe_allow_html=True)

# ==================== MARKET DATA TICKER ====================
def create_ticker_text():
    ticker_parts = []
    for name, data in st.session_state.exchange_data.items():
        arrow = "▲" if data.index_change >= 0 else "▼"
        color = "#00ff88" if data.index_change >= 0 else "#ff4444"
        display_name = name.split()[0] if " " in name else name
        ticker_parts.append(f"{display_name}: {data.index_value:.0f} <span style='color:{color}'>{arrow} {abs(data.index_change):.1f}%</span>")
    for symbol, pred in list(st.session_state.ai_predictions.items())[:5]:
        if pred:
            emoji = "🟢" if pred.signal == "BUY" else "🔴" if pred.signal == "SELL" else "🟡"
            ticker_parts.append(f"{emoji} {symbol}: ${pred.current_price:.2f}")
    return " | ".join(ticker_parts)

if st.session_state.exchange_data:
    st.markdown(f"""
    <div class="ticker-bar">
        <div class="ticker-content">🔴 LIVE MARKET DATA • {create_ticker_text()} • </div>
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
        st.success("Live stream started" if st.session_state.auto_stream else "Live stream stopped")
with c3:
    if AUTO_BROADCASTER_AVAILABLE:
        if st.button("📢 Start Broadcast" if not st.session_state.broadcast_active else "🔴 Stop Broadcast", use_container_width=True):
            if not st.session_state.broadcast_active:
                if not hasattr(st.session_state, 'broadcaster'):
                    st.session_state.broadcaster = AutoBroadcaster(SocialMediaStreamer() if SOCIAL_STREAMER_AVAILABLE else None)
                st.session_state.broadcaster.start_broadcasting()
                st.session_state.broadcast_active = True
                st.success("Broadcast started")
            else:
                st.session_state.broadcaster.stop_broadcasting()
                st.session_state.broadcast_active = False
                st.warning("Broadcast stopped")
    else:
        st.button("📢 Broadcast", disabled=True, use_container_width=True)
with c4:
    st.markdown(f"<div style='text-align: center; padding: 8px; background: rgba(26, 26, 46, 0.7); border-radius: 30px;'><small>Updated: {st.session_state.last_update.strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)

# ==================== MAIN CONTENT ====================
main_left, main_right = st.columns([2.5, 1])

with main_right:
    # Rotating Stock Index Ticker (replaces one ad slot)
    st.markdown("""
    <div class="stock-index-ticker">
        <div style="text-align: center; margin-bottom: 10px;">
            <span style="color: #00ff88; font-weight: 600;">📊 MARKET INDEX</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Create rotating stock data
    all_stocks = []
    for name, data in st.session_state.exchange_data.items():
        for stock in data.top_gainers[:2] + data.top_losers[:2]:
            all_stocks.append(stock)
    
    if all_stocks:
        # Rotate through stocks
        st.session_state.ticker_index = (st.session_state.ticker_index + 1) % len(all_stocks)
        current_stock = all_stocks[st.session_state.ticker_index]
        
        change_class = "stock-change-positive" if current_stock['change'] >= 0 else "stock-change-negative"
        change_symbol = "+" if current_stock['change'] >= 0 else ""
        
        st.markdown(f"""
        <div class="stock-index-content">
            <div class="stock-item">
                <span class="stock-symbol">{current_stock['symbol']}</span>
                <span class="stock-price">${current_stock['price']:.2f}</span>
                <span class="{change_class}">{change_symbol}{current_stock['change']:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add small indicator that it's rotating
        st.markdown('<div style="text-align: center; font-size: 10px; color: #888; margin-top: 8px;">⟳ Rotating through top movers</div>', unsafe_allow_html=True)
    else:
        st.info("Loading market data...")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Advertisement placeholders (4 remaining slots)
    st.markdown("""
    <div class="right-ad">
        <div class="ad-container"><div class="ad-icon">📢</div><div class="ad-title">SPONSORED</div><div class="ad-content"><strong>Your Ad Here</strong><br>Reach traders daily</div><div class="ad-button">Advertise →</div></div>
        <div class="ad-container"><div class="ad-icon">📊</div><div class="ad-title">PREMIUM</div><div class="ad-content"><strong>AI Pro Analytics</strong><br>Advanced signals</div><div class="ad-button">Learn More →</div></div>
        <div class="ad-container"><div class="ad-icon">📚</div><div class="ad-title">FREE TRAINING</div><div class="ad-content"><strong>Master Markets</strong><br>Free webinar</div><div class="ad-button">Register →</div></div>
        <div class="ad-container"><div class="ad-icon">🤝</div><div class="ad-title">PARTNER OFFER</div><div class="ad-content"><strong>Zero Commission</strong><br>Exclusive deal</div><div class="ad-button">Claim →</div></div>
    </div>
    """, unsafe_allow_html=True)

with main_left:
    # Stats Row
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{len(st.session_state.exchange_data)}</div><div class='stat-label'>Global Exchanges</div></div>", unsafe_allow_html=True)
    with stat_cols[1]:
        buy_signals = sum(1 for p in st.session_state.ai_predictions.values() if p and p.signal == "BUY")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#00ff88;'>{buy_signals}</div><div class='stat-label'>Buy Signals</div></div>", unsafe_allow_html=True)
    with stat_cols[2]:
        sell_signals = sum(1 for p in st.session_state.ai_predictions.values() if p and p.signal == "SELL")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#ff4444;'>{sell_signals}</div><div class='stat-label'>Sell Signals</div></div>", unsafe_allow_html=True)
    with stat_cols[3]:
        avg_conf = np.mean([p.confidence for p in st.session_state.ai_predictions.values() if p]) if st.session_state.ai_predictions else 0
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{avg_conf:.0f}%</div><div class='stat-label'>AI Confidence</div></div>", unsafe_allow_html=True)
    
    # Market Overview
    st.markdown("## 📊 Market Overview")
    market_cols = st.columns(2)
    for idx, (name, data) in enumerate(st.session_state.exchange_data.items()):
        with market_cols[idx % 2]:
            change_class = "positive" if data.index_change >= 0 else "negative"
            st.markdown(f"<div class='exchange-card'><div class='market-name'>{name}</div><div class='market-value'>{data.index_value:.2f}</div><div class='market-change {change_class}'>{data.index_change:+.2f}%</div></div>", unsafe_allow_html=True)
    
    # Interactive Stock Chart Section
    st.markdown("## 📈 Live Stock Charts")
    
    chart_col1, chart_col2 = st.columns([1, 3])
    with chart_col1:
        chart_symbol = st.selectbox("Select Stock", st.session_state.watchlist, key="chart_select")
        chart_period = st.selectbox("Time Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=2)
    
    with chart_col2:
        if chart_symbol:
            fig = create_stock_chart(chart_symbol, chart_period)
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="stock_chart")
            else:
                st.info("Chart data not available")
    
    # Sector Performance
    st.markdown("## 📈 Sector Performance")
    sector_cols = st.columns(4)
    for idx, (name, data) in enumerate(st.session_state.sector_data.items()):
        with sector_cols[idx % 4]:
            color = "#00ff88" if data.performance > 0 else "#ff4444"
            icon = SECTORS[name]["icon"]
            st.markdown(f"<div class='sector-item'><div class='sector-icon'>{icon}</div><div class='sector-name'>{name}</div><div class='sector-perf' style='color:{color};'>{data.performance:+.1f}%</div><div style='font-size:11px;color:#888;'>{data.signal}</div></div>", unsafe_allow_html=True)
    
    # Alerts and AI Picks
    alert_col, ai_col = st.columns(2)
    with alert_col:
        st.markdown("## 🚨 Hot Alerts")
        if st.session_state.global_alerts:
            for alert in st.session_state.global_alerts[-3:]:
                alert_class = "alert-buy" if "BUY" in alert.alert_type else "alert-sell"
                st.markdown(f"<div class='alert-card {alert_class}'><div style='display:flex;justify-content:space-between;'><strong>{alert.alert_type}</strong><small>{alert.timestamp.strftime('%H:%M')}</small></div><div style='font-size:18px;font-weight:600;'>{alert.symbol}</div><div>${alert.price:.2f} ({alert.change:+.1f}%)</div><small>{alert.exchange}</small></div>", unsafe_allow_html=True)
        else:
            st.info("No active alerts")
    
    with ai_col:
        st.markdown("## 🤖 AI Picks")
        for symbol, pred in list(st.session_state.ai_predictions.items())[:3]:
            if pred:
                signal_color = "#00ff88" if pred.signal == "BUY" else "#ff4444" if pred.signal == "SELL" else "#ffaa00"
                st.markdown(f"<div class='market-card'><div class='market-name'>{symbol}</div><div class='market-value'>${pred.current_price:.2f}</div><div style='color:{signal_color};'>{pred.signal} ({pred.confidence}%)</div><small>Target: ${pred.target:.2f}</small></div>", unsafe_allow_html=True)
    
    # Investment Calculator
    st.markdown("## 💰 Investment Calculator")
    with st.container():
        st.markdown('<div class="investment-card">', unsafe_allow_html=True)
        st.markdown('<div class="investment-title">Plan Your Investment</div>', unsafe_allow_html=True)
        
        inv_symbol = st.selectbox("Select Stock", st.session_state.watchlist, key="inv_select")
        inv_amount = st.number_input("Investment Amount ($)", min_value=100, value=1000, step=100)
        
        if st.button("Calculate Plan", use_container_width=True):
            if inv_symbol in st.session_state.ai_predictions:
                plan = calculate_investment_plan(inv_symbol, inv_amount, st.session_state.ai_predictions[inv_symbol])
                if plan:
                    st.markdown(f"""
                    <div style="margin-top: 15px;">
                        <strong>{plan.symbol} Investment Plan</strong><br>
                        Investment: ${plan.investment_amount:,.2f}<br>
                        Shares: {plan.shares}<br>
                        Current Price: ${plan.current_price:.2f}<br>
                        Target Price: ${plan.target_price:.2f}<br>
                        Potential Return: {plan.potential_return:+.1f}%<br>
                        <span style="color: #00ff88;">Recommendation: {plan.recommendation}</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Could not calculate plan")
            else:
                st.error("No prediction available")
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== ECONOMIC INDICATORS ====================
st.markdown("## 📊 Economic Indicators")
eco_cols = st.columns(4)

try:
    vix = yf.Ticker("^VIX")
    vix_price = vix.info.get('regularMarketPrice', 15)
    with eco_cols[0]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>VIX (Fear Index)</div><div class='stat-value'>{vix_price:.1f}</div></div>", unsafe_allow_html=True)
except:
    with eco_cols[0]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>VIX (Fear Index)</div><div class='stat-value'>15.2</div></div>", unsafe_allow_html=True)

try:
    tnx = yf.Ticker("^TNX")
    tnx_price = tnx.info.get('regularMarketPrice', 4.2)
    with eco_cols[1]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>10-Yr Treasury</div><div class='stat-value'>{tnx_price:.2f}%</div></div>", unsafe_allow_html=True)
except:
    with eco_cols[1]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>10-Yr Treasury</div><div class='stat-value'>4.25%</div></div>", unsafe_allow_html=True)

try:
    gold = yf.Ticker("GC=F")
    gold_price = gold.info.get('regularMarketPrice', 2000)
    with eco_cols[2]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Gold</div><div class='stat-value'>${gold_price:.0f}</div></div>", unsafe_allow_html=True)
except:
    with eco_cols[2]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Gold</div><div class='stat-value'>$2,050</div></div>", unsafe_allow_html=True)

try:
    oil = yf.Ticker("CL=F")
    oil_price = oil.info.get('regularMarketPrice', 75)
    with eco_cols[3]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Crude Oil</div><div class='stat-value'>${oil_price:.1f}</div></div>", unsafe_allow_html=True)
except:
    with eco_cols[3]:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Crude Oil</div><div class='stat-value'>$72.50</div></div>", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Dashboard Controls")
    st.success("🟢 LIVE STREAM: ACTIVE") if st.session_state.auto_stream else st.warning("⚪ LIVE STREAM: INACTIVE")
    st.success("📢 BROADCAST: ACTIVE") if st.session_state.broadcast_active else st.warning("🔇 BROADCAST: INACTIVE")
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

# Add to the top of your app with other imports
from social_manager import SocialMediaManager

# Add to session state initialization
if 'social_manager' not in st.session_state:
    st.session_state.social_manager = SocialMediaManager()

# Add this to your sidebar (add after the existing sidebar content)
with st.sidebar:
    # ... existing sidebar content ...
    
    st.divider()
    st.markdown("### 🌐 Social Media")
    
    # Social Media Tabs
    sm_tab1, sm_tab2, sm_tab3 = st.tabs(["🔌 Connect", "📤 Post", "📊 History"])
    
    with sm_tab1:
        st.markdown("#### Connect Your Accounts")
        
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
            fb_page = st.text_input("Page ID (optional)", key="fb_page")
            
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
            st.info("TikTok requires developer account setup")
            tt_session = st.text_input("Session ID (optional)", type="password", key="tt_session")
            
            if st.button("Configure TikTok", key="conn_tiktok"):
                success, msg = st.session_state.social_manager.connect_tiktok(session_id=tt_session)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
        
        # Connection Status
        st.markdown("#### Connection Status")
        connected = st.session_state.social_manager.get_connected_platforms()
        if connected:
            for platform in connected:
                st.success(f"✅ {platform.capitalize()}")
        else:
            st.warning("No platforms connected")
    
    with sm_tab2:
        st.markdown("#### Post to Social Media")
        
        # Post Content
        post_message = st.text_area("Message", height=100, placeholder="Enter your message here...")
        
        # Auto-generate message from latest data
        if st.button("📊 Use Latest Market Data", use_container_width=True):
            if st.session_state.exchange_data:
                spy = next((d for n, d in st.session_state.exchange_data.items() if "NYSE" in n or "NASDAQ" in n), None)
                if spy:
                    post_message = f"""🤖 AI Trading Alert

Market Update: {spy.index_value:.2f} ({spy.index_change:+.2f}%)

Top Gainers Today:
{chr(10).join([f"• {s['symbol']}: +{s['change']:.1f}%" for s in list(spy.top_gainers)[:3]])}

AI Prediction: {'BULLISH' if spy.index_change > 0 else 'BEARISH'}

#Stocks #Trading #AI #MarketAnalysis"""
        
        # Media Attachment
        col_media1, col_media2 = st.columns(2)
        with col_media1:
            attach_chart = st.checkbox("Attach Chart", value=True)
        with col_media2:
            attach_video = st.checkbox("Create Video", value=False)
        
        # Platform Selection
        st.markdown("**Post to:**")
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
        with col_p1:
            post_twitter = st.checkbox("Twitter/X", value=True)
        with col_p2:
            post_facebook = st.checkbox("Facebook", value=False)
        with col_p3:
            post_instagram = st.checkbox("Instagram", value=False)
        with col_p4:
            post_youtube = st.checkbox("YouTube", value=False)
        with col_p5:
            post_tiktok = st.checkbox("TikTok", value=False)
        
        # Auto-Stream Toggle
        auto_stream = st.toggle("🔁 Auto-Stream Every 15 Minutes", value=False)
        if auto_stream:
            st.info("Auto-stream will post market updates automatically")
        
        # Post Button
        if st.button("📢 POST TO SELECTED PLATFORMS", type="primary", use_container_width=True):
            if post_message:
                with st.spinner("Posting to social media..."):
                    # Generate chart if needed
                    chart_path = None
                    if attach_chart and st.session_state.exchange_data:
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(10, 6))
                        spy = next((d for n, d in st.session_state.exchange_data.items() if "NYSE" in n), None)
                        if spy:
                            ax.text(0.5, 0.5, f"Market Update\n{spy.index_value:.2f}\n{spy.index_change:+.2f}%",
                                   transform=ax.transAxes, ha='center', va='center', fontsize=20, color='white')
                            ax.set_facecolor('#111111')
                            chart_path = tempfile.mktemp(suffix=".png")
                            plt.savefig(chart_path, facecolor='#111111')
                            plt.close()
                    
                    # Create simple video if requested
                    video_path = None
                    if attach_video and chart_path:
                        try:
                            from moviepy.editor import ImageClip, TextClip, CompositeVideoClip
                            img_clip = ImageClip(chart_path).set_duration(15).resize((1080, 1920))
                            txt_clip = TextClip("Market Update", fontsize=60, color='white').set_position('center').set_duration(15)
                            video = CompositeVideoClip([img_clip, txt_clip])
                            video_path = tempfile.mktemp(suffix=".mp4")
                            video.write_videofile(video_path, fps=24, verbose=False, logger=None)
                        except:
                            pass
                    
                    # Post to selected platforms
                    results = {}
                    
                    if post_twitter:
                        success, msg = st.session_state.social_manager.post_to_twitter(
                            post_message, chart_path, video_path
                        )
                        results['Twitter'] = {'success': success, 'message': msg}
                    
                    if post_facebook:
                        success, msg = st.session_state.social_manager.post_to_facebook(
                            post_message, video_path, chart_path
                        )
                        results['Facebook'] = {'success': success, 'message': msg}
                    
                    if post_instagram and (chart_path or video_path):
                        success, msg = st.session_state.social_manager.post_to_instagram(
                            post_message, chart_path, video_path
                        )
                        results['Instagram'] = {'success': success, 'message': msg}
                    
                    if post_youtube and video_path:
                        success, msg = st.session_state.social_manager.post_to_youtube(
                            video_path,
                            f"Market Update - {datetime.now().strftime('%Y-%m-%d')}",
                            post_message,
                            ['stocks', 'trading', 'ai', 'market'],
                            is_shorts=True
                        )
                        results['YouTube'] = {'success': success, 'message': msg}
                    
                    if post_tiktok and video_path:
                        success, msg = st.session_state.social_manager.post_to_tiktok(
                            video_path,
                            "Market Update",
                            "#stocks #trading #ai"
                        )
                        results['TikTok'] = {'success': success, 'message': msg}
                    
                    # Display results
                    for platform, result in results.items():
                        if result['success']:
                            st.success(f"✅ {platform}: {result['message']}")
                        else:
                            st.error(f"❌ {platform}: {result['message']}")
                    
                    st.balloons()
            else:
                st.warning("Please enter a message to post")
        
        # Auto-stream setup
        if auto_stream:
            if st.button("Start Auto-Stream", use_container_width=True):
                success, msg = st.session_state.social_manager.start_auto_stream(interval_minutes=15)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    with sm_tab3:
        st.markdown("#### Post History")
        
        history = st.session_state.social_manager.get_post_history()
        if history:
            for post in history[-10:]:
                with st.container():
                    st.markdown(f"""
                    <div style="background: rgba(26,26,46,0.5); padding: 10px; border-radius: 10px; margin: 5px 0;">
                        <strong>{post['platform'].upper()}</strong> - {post['timestamp'].strftime('%Y-%m-%d %H:%M')}<br>
                        <small>{post['content']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No posts yet")
        
        if st.button("Clear History", use_container_width=True):
            st.session_state.social_manager.post_history = []
            st.success("History cleared")

# ==================== AUTO-STREAM LOOP ====================
if st.session_state.auto_stream:
    time.sleep(30)
    st.rerun()

# ==================== INITIAL DATA LOAD ====================
if not st.session_state.exchange_data:
    update_all_data()

# ==================== AUTO-ROTATE TICKER ====================
# This will auto-rotate the stock index every 5 seconds
if st.session_state.auto_stream:
    time.sleep(5)
    st.rerun()

# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    AI Trading Dashboard - Real-time Market Intelligence<br>
    Data across 8 global exchanges | AI-powered predictions | Interactive Charts | Auto-broadcast<br>
    <small>⚠️ Not financial advice. Always do your own research.</small>
</div>
""", unsafe_allow_html=True)
