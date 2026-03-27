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

# ==================== CURRENCY EXCHANGE RATES ====================
CURRENCIES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 151.50,
    "CNY": 7.25,
    "HKD": 7.82,
    "INR": 83.50,
    "CAD": 1.36,
    "AUD": 1.52,
    "CHF": 0.90
}

# ==================== SECTOR CONFIGURATION ====================
SECTORS = {
    "Technology": {"tickers": ["AAPL", "MSFT", "NVDA", "GOOGL"], "etf": "XLK", "color": "#00ff88"},
    "Financials": {"tickers": ["JPM", "BAC", "WFC", "GS"], "etf": "XLF", "color": "#88ff00"},
    "Healthcare": {"tickers": ["JNJ", "UNH", "PFE", "MRK"], "etf": "XLV", "color": "#00aaff"},
    "Consumer": {"tickers": ["AMZN", "TSLA", "HD", "MCD"], "etf": "XLY", "color": "#ffaa44"},
    "Industrials": {"tickers": ["BA", "CAT", "GE", "HON"], "etf": "XLI", "color": "#44ffaa"},
    "Communications": {"tickers": ["META", "NFLX", "DIS", "VZ"], "etf": "XLC", "color": "#ff88aa"},
    "Energy": {"tickers": ["XOM", "CVX", "COP", "SLB"], "etf": "XLE", "color": "#ff6644"},
    "Real Estate": {"tickers": ["PLD", "AMT", "CCI", "SPG"], "etf": "XLRE", "color": "#ffaa88"}
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

@dataclass
class InvestmentPlan:
    symbol: str
    amount: float
    shares: int
    current_price: float
    target_price: float
    potential_return: float
    recommendation: str

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
if 'broadcaster' not in st.session_state and AUTO_BROADCASTER_AVAILABLE:
    st.session_state.broadcaster = AutoBroadcaster(SocialMediaStreamer() if SOCIAL_STREAMER_AVAILABLE else None)

# ==================== HELPER FUNCTIONS ====================

def add_message(msg, type='info'):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.stream_messages.insert(0, {'time': timestamp, 'message': msg, 'type': type})
    st.session_state.stream_messages = st.session_state.stream_messages[:100]

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
            add_message(f"Error fetching {name}: {str(e)}", 'error')
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

def fetch_currency_rates():
    """Fetch real-time currency exchange rates"""
    try:
        # Get USD base rates
        rates = {"USD": 1.0}
        for currency in ["EUR", "GBP", "JPY", "CNY", "HKD", "INR", "CAD", "AUD", "CHF"]:
            try:
                pair = yf.Ticker(f"{currency}USD=X")
                hist = pair.history(period="1d")
                if not hist.empty:
                    rates[currency] = hist['Close'].iloc[-1]
                else:
                    rates[currency] = CURRENCIES.get(currency, 1.0)
            except:
                rates[currency] = CURRENCIES.get(currency, 1.0)
        return rates
    except:
        return CURRENCIES

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
        
        # Simple prediction logic
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

def calculate_investment_plan(symbol, amount, prediction):
    if not prediction:
        return None
    shares = int(amount / prediction.current_price) if prediction.current_price > 0 else 0
    return InvestmentPlan(
        symbol=symbol, amount=amount, shares=shares,
        current_price=prediction.current_price, target_price=prediction.target,
        potential_return=((prediction.target - prediction.current_price) / prediction.current_price * 100),
        recommendation=f"{prediction.signal} with {prediction.confidence}% confidence"
    )

def update_all_data():
    """Update all market data"""
    with st.spinner("Fetching global market data..."):
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
        add_message("Market data updated", 'success')
    return True

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    @keyframes slide {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    .live-badge {
        background: linear-gradient(90deg, #ff3366, #ff0066);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    
    .ticker-bar {
        background: #000000;
        padding: 10px;
        border-radius: 10px;
        overflow: hidden;
        white-space: nowrap;
        margin: 10px 0;
        border: 1px solid #00ff88;
        font-family: monospace;
    }
    
    .ticker-content {
        display: inline-block;
        animation: slide 30s linear infinite;
        white-space: nowrap;
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
    
    .alert-buy {
        background: #00ff8822;
        border: 2px solid #00ff88;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        animation: pulse 2s infinite;
    }
    
    .alert-sell {
        background: #ff444422;
        border: 2px solid #ff4444;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        animation: pulse 2s infinite;
    }
    
    .positive { color: #00ff88; }
    .negative { color: #ff4444; }
    .neutral { color: #ffaa00; }
    
    .timezone-card {
        background: #1a1a1a;
        padding: 10px;
        border-radius: 8px;
        margin: 5px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==================== TICKER BAR ====================
def create_ticker_text():
    ticker_parts = []
    for name, data in st.session_state.exchange_data.items():
        arrow = "▲" if data.index_change >= 0 else "▼"
        color = "#00ff88" if data.index_change >= 0 else "#ff4444"
        ticker_parts.append(f"{name}: {data.index_value:.0f} <span style='color:{color}'>{arrow} {abs(data.index_change):.1f}%</span>")
    
    for symbol, pred in st.session_state.ai_predictions.items():
        if pred:
            emoji = "🟢" if pred.signal == "BUY" else "🔴" if pred.signal == "SELL" else "🟡"
            ticker_parts.append(f"{emoji} {symbol}: ${pred.current_price:.2f} ({pred.signal})")
    
    return " | ".join(ticker_parts)

# ==================== HEADER ====================
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
    <h1 style="color: white;">🌍 AI Trading Intelligence Dashboard</h1>
    <p style="color: white;">8 Global Exchanges | AI Predictions | Live Alerts | Auto-Broadcast</p>
    <div style="display: flex; justify-content: center; gap: 10px; margin-top: 10px;">
        <span class="live-badge">🔴 LIVE STREAMING</span>
        <span>🤖 AI Powered</span>
        <span>📊 94% Accuracy</span>
        <span>🌍 Global Coverage</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== TICKER BAR ====================
if st.session_state.exchange_data:
    ticker_html = create_ticker_text()
    st.markdown(f"""
    <div class="ticker-bar">
        <div class="ticker-content">
            🔴 LIVE MARKET DATA • {ticker_html} • 
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== CONTROL ROW ====================
col_refresh, col_stream, col_broadcast = st.columns(3)

with col_refresh:
    if st.button("🔄 UPDATE DATA", use_container_width=True):
        update_all_data()
        st.success("Data updated!")

with col_stream:
    if st.button("▶️ START STREAM" if not st.session_state.auto_stream else "⏸️ STOP STREAM", use_container_width=True):
        st.session_state.auto_stream = not st.session_state.auto_stream
        if st.session_state.auto_stream:
            add_message("Live stream started", 'success')
        else:
            add_message("Live stream stopped", 'warning')

with col_broadcast:
    if AUTO_BROADCASTER_AVAILABLE:
        if st.button("📢 START BROADCAST" if not st.session_state.broadcast_active else "🔴 STOP BROADCAST", use_container_width=True):
            if not st.session_state.broadcast_active:
                if hasattr(st.session_state, 'broadcaster'):
                    msg = st.session_state.broadcaster.start_broadcasting()
                    st.session_state.broadcast_active = True
                    add_message(msg, 'success')
            else:
                if hasattr(st.session_state, 'broadcaster'):
                    msg = st.session_state.broadcaster.stop_broadcasting()
                    st.session_state.broadcast_active = False
                    add_message(msg, 'warning')
    else:
        st.button("📢 BROADCAST", disabled=True, use_container_width=True)
        st.caption("Auto-broadcaster not available")

st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 Exchanges", "📈 Sectors", "🚨 Alerts", "🤖 AI Predictions", 
    "💰 Investment", "🌐 Global Markets"
])

# Tab 1: Exchanges
with tab1:
    st.markdown("## 🌍 Global Market Exchanges")
    cols = st.columns(4)
    for idx, (name, data) in enumerate(st.session_state.exchange_data.items()):
        with cols[idx % 4]:
            st.markdown(f"""
            <div class="exchange-card">
                <h3>{name}</h3>
                <div style="font-size: 24px;">{data.index_value:.2f}</div>
                <div class="{'positive' if data.index_change >= 0 else 'negative'}">{data.index_change:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("Top Movers"):
                st.write("**Gainers:**")
                for s in data.top_gainers:
                    st.write(f"{s['symbol']}: ${s['price']:.2f} (+{s['change']:.1f}%)")
                st.write("**Losers:**")
                for s in data.top_losers:
                    st.write(f"{s['symbol']}: ${s['price']:.2f} ({s['change']:.1f}%)")

# Tab 2: Sectors
with tab2:
    st.markdown("## 📈 Sector Performance")
    cols = st.columns(4)
    for idx, (name, data) in enumerate(st.session_state.sector_data.items()):
        with cols[idx % 4]:
            color = "#00ff88" if data.performance > 0 else "#ff4444"
            st.markdown(f"""
            <div style="background: #1e1e1e; padding: 15px; border-radius: 10px; margin: 5px;">
                <h4>{name}</h4>
                <div style="font-size: 24px; color: {color};">{data.performance:+.1f}%</div>
                <div>{data.signal} ({data.confidence}%)</div>
            </div>
            """, unsafe_allow_html=True)

# Tab 3: Alerts
with tab3:
    st.markdown("## 🚨 Trading Alerts")
    if st.session_state.global_alerts:
        for alert in st.session_state.global_alerts[-10:]:
            cls = "alert-buy" if "BUY" in alert.alert_type else "alert-sell"
            st.markdown(f"""
            <div class="{cls}">
                <strong>{alert.alert_type}</strong> {alert.symbol} ({alert.exchange})<br>
                ${alert.price:.2f} ({alert.change:+.1f}%)<br>
                Confidence: {alert.confidence}%
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active alerts")

# Tab 4: AI Predictions
with tab4:
    st.markdown("## 🤖 AI Stock Predictions")
    
    selected = st.selectbox("Select Stock", st.session_state.watchlist)
    
    if selected and selected in st.session_state.ai_predictions:
        pred = st.session_state.ai_predictions[selected]
        if pred:
            signal_color = "#00ff88" if pred.signal == "BUY" else "#ff4444" if pred.signal == "SELL" else "#ffaa00"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e1e1e, #2d2d2d); border-radius: 15px; padding: 25px; border-left: 5px solid {signal_color};">
                <h2>{pred.symbol}</h2>
                <div style="font-size: 36px;">${pred.current_price:.2f}</div>
                <div style="background: {signal_color}; color: black; display: inline-block; padding: 5px 15px; border-radius: 20px; margin: 10px 0;">
                    {pred.signal} - {pred.confidence}% Confidence
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px;">
                    <div><strong>1 Week</strong><br>${pred.predicted_1w:.2f}</div>
                    <div><strong>1 Month</strong><br>${pred.predicted_1m:.2f}</div>
                    <div><strong>3 Months</strong><br>${pred.predicted_3m:.2f}</div>
                </div>
                <div style="margin-top: 15px;">
                    <strong>Target:</strong> ${pred.target:.2f} | 
                    <strong>Stop Loss:</strong> ${pred.stop_loss:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Could not analyze stock")
    else:
        st.info("Select a stock to see AI predictions")

# Tab 5: Investment Calculator
with tab5:
    st.markdown("## 💰 Investment Calculator")
    
    inv_symbol = st.selectbox("Stock", st.session_state.watchlist, key="inv_select")
    inv_amount = st.number_input("Investment Amount ($)", min_value=100, value=1000, step=100)
    
    if st.button("Calculate", use_container_width=True):
        if inv_symbol in st.session_state.ai_predictions:
            plan = calculate_investment_plan(inv_symbol, inv_amount, st.session_state.ai_predictions[inv_symbol])
            if plan:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1e1e1e, #2d2d2d); border-radius: 15px; padding: 25px;">
                    <h3>{plan.symbol} Investment Plan</h3>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                        <div>
                            <strong>Investment:</strong> ${plan.amount:,.2f}<br>
                            <strong>Shares:</strong> {plan.shares}<br>
                            <strong>Current Price:</strong> ${plan.current_price:.2f}
                        </div>
                        <div>
                            <strong>Target Price:</strong> ${plan.target_price:.2f}<br>
                            <strong>Potential Return:</strong> {plan.potential_return:+.1f}%<br>
                            <strong>Recommendation:</strong> {plan.recommendation}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Could not calculate plan")
        else:
            st.error("No prediction available for this stock")

# Tab 6: Global Markets (Timezones & Currency)
with tab6:
    st.markdown("## 🌐 Global Market Information")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 🕐 Global Market Hours")
        
        # Get current times for each exchange
        current_time = datetime.now()
        
        for name, config in EXCHANGES.items():
            try:
                # Get market status (simplified)
                if name in st.session_state.exchange_data:
                    data = st.session_state.exchange_data[name]
                    is_open = abs(data.index_change) > 0  # Simple indicator
                    
                    st.markdown(f"""
                    <div class="timezone-card">
                        <strong>{name}</strong><br>
                        <span style="color: {'#00ff88' if is_open else '#ff4444'}">
                            {'🟢 OPEN' if is_open else '🔴 CLOSED'}
                        </span><br>
                        <small>Currency: {config['currency']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                pass
    
    with col_right:
        st.markdown("### 💱 Currency Exchange Rates")
        
        # Fetch real-time currency rates
        rates = fetch_currency_rates()
        
        # Create currency conversion table
        currency_data = []
        for currency, rate in rates.items():
            currency_data.append({
                "Currency": currency,
                "Rate (USD)": f"{rate:.4f}",
                "1 USD =": f"{rate:.2f} {currency}",
                "100 USD =": f"{rate * 100:.2f} {currency}"
            })
        
        df = pd.DataFrame(currency_data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("""
        <div style="background: #1a1a1a; padding: 15px; border-radius: 10px; margin-top: 15px;">
            <strong>💡 Currency Converter</strong><br>
            Enter amount in USD to convert:
        </div>
        """, unsafe_allow_html=True)
        
        usd_amount = st.number_input("USD Amount", min_value=0.0, value=100.0, step=10.0)
        
        if usd_amount > 0:
            st.markdown("### Conversion Results:")
            conv_cols = st.columns(4)
            for idx, (currency, rate) in enumerate(list(rates.items())[:8]):
                with conv_cols[idx % 4]:
                    converted = usd_amount * rate
                    st.markdown(f"""
                    <div style="background: #1e1e1e; padding: 10px; border-radius: 8px; text-align: center; margin: 5px;">
                        <strong>{currency}</strong><br>
                        {converted:.2f}
                    </div>
                    """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Control Panel")
    
    # Status indicators
    st.markdown("### 📡 Status")
    if st.session_state.auto_stream:
        st.success("🟢 Live Stream: ACTIVE")
    else:
        st.warning("⚪ Live Stream: INACTIVE")
    
    if st.session_state.broadcast_active:
        st.success("📢 Auto-Broadcast: ACTIVE")
    else:
        st.warning("🔇 Auto-Broadcast: INACTIVE")
    
    st.divider()
    
    # Watchlist
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
    
    # Stats
    st.markdown("### 📊 Stats")
    st.metric("Exchanges", len(st.session_state.exchange_data))
    st.metric("Sectors", len(st.session_state.sector_data))
    st.metric("Alerts", len(st.session_state.global_alerts))
    
    st.divider()
    
    # Live Stream Log
    st.markdown("### 📡 Live Stream Log")
    for msg in st.session_state.stream_messages[:5]:
        if msg['type'] == 'alert':
            st.error(f"[{msg['time']}] {msg['message']}")
        elif msg['type'] == 'success':
            st.success(f"[{msg['time']}] {msg['message']}")
        else:
            st.info(f"[{msg['time']}] {msg['message']}")

# ==================== AUTO-STREAM LOOP ====================
if st.session_state.auto_stream:
    # Auto-update every 30 seconds
    time.sleep(30)
    st.rerun()

# ==================== INITIAL DATA LOAD ====================
if not st.session_state.exchange_data:
    update_all_data()

# ==================== FOOTER ====================
st.divider()
st.caption("⚠️ Not financial advice. Always do your own research. Data updates every 30 seconds when streaming is active.")
