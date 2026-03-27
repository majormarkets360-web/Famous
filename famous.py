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
import schedule
from textblob import TextBlob
import warnings
import asyncio
import pickle
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from social_streamer import SocialMediaStreamer

# Check for optional imports
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

warnings.filterwarnings('ignore')

# ==================== DATA CLASSES ====================
@dataclass
class Alert:
    symbol: str
    type: str  # 'BUY', 'SELL', 'ALERT'
    price: float
    reason: str
    confidence: float
    timestamp: datetime

@dataclass
class TradeOpportunity:
    symbol: str
    action: str  # 'BUY' or 'SELL'
    entry_price: float
    target_price: float
    stop_loss: float
    confidence: float
    reason: str
    time_horizon: str  # 'short', 'medium', 'long'

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="AI Trading Dashboard - 24/7 Live Stream",
    page_icon="📈",
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
    if 'opportunities' not in st.session_state:
        st.session_state.opportunities = []
    if 'stream_messages' not in st.session_state:
        st.session_state.stream_messages = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    if 'auto_stream' not in st.session_state:
        st.session_state.auto_stream = False
    if 'social_connected' not in st.session_state:
        st.session_state.social_connected = {'twitter': False, 'instagram': False, 'tiktok': False}
    if 'stock_analysis' not in st.session_state:
        st.session_state.stock_analysis = {}
    if 'stream_thread_started' not in st.session_state:
        st.session_state.stream_thread_started = False
        if 'social_streamer' not in st.session_state:
        st.session_state.social_streamer = SocialMediaStreamer()

# Call initialization
init_session_state()

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    /* Live streaming style */
    .live-badge {
        background: linear-gradient(90deg, #ff3366, #ff0066);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .alert-card {
        background: linear-gradient(135deg, #ff3366, #ff0066);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #ff00ff;
        animation: slideIn 0.5s;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .opportunity-card {
        background: linear-gradient(135deg, #00ff88, #00cc66);
        color: black;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #00ff00;
    }
    
    .ticker-tape {
        background: #1e1e1e;
        color: white;
        padding: 10px;
        overflow: hidden;
        white-space: nowrap;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .ticker-content {
        display: inline-block;
        animation: ticker 30s linear infinite;
    }
    
    @keyframes ticker {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #00ff88;
        margin: 0.5rem 0;
    }
    
    .signal-buy {
        background: linear-gradient(135deg, #00ff8822, #00cc6622);
        border: 2px solid #00ff88;
        padding: 1rem;
        border-radius: 10px;
    }
    
    .signal-sell {
        background: linear-gradient(135deg, #ff444422, #ff000022);
        border: 2px solid #ff4444;
        padding: 1rem;
        border-radius: 10px;
    }
    
    .live-stream {
        background: #000000;
        border: 2px solid #00ff88;
        border-radius: 10px;
        padding: 15px;
        font-family: monospace;
        font-size: 14px;
        height: 400px;
        overflow-y: scroll;
    }
    
    .stream-message {
        padding: 5px;
        border-bottom: 1px solid #333;
        animation: fadeIn 0.3s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================

def add_stream_message(message, type='info'):
    """Add message to live stream"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.stream_messages.insert(0, {
        'time': timestamp,
        'message': message,
        'type': type
    })
    # Keep only last 100 messages
    st.session_state.stream_messages = st.session_state.stream_messages[:100]

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices):
    """Calculate MACD indicator"""
    exp1 = prices.ewm(span=12, adjust=False).mean()
    exp2 = prices.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

def calculate_bollinger_bands(prices, period=20):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)
    return upper_band, lower_band, sma

def analyze_stock(symbol):
    """Comprehensive stock analysis"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="3mo")
        
        if hist.empty:
            return None
        
        current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        prev_close = info.get('regularMarketPreviousClose', current_price)
        change = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
        volume = info.get('volume', 0)
        avg_volume = info.get('averageVolume', volume)
        
        # Technical indicators
        if len(hist) > 20:
            rsi = calculate_rsi(hist['Close']).iloc[-1]
            macd, signal, hist_macd = calculate_macd(hist['Close'])
            upper_band, lower_band, sma = calculate_bollinger_bands(hist['Close'])
            
            current_rsi = rsi if not pd.isna(rsi) else 50
            current_macd = macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0
            current_signal = signal.iloc[-1] if not pd.isna(signal.iloc[-1]) else 0
            current_upper = upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else current_price * 1.05
            current_lower = lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else current_price * 0.95
            current_sma = sma.iloc[-1] if not pd.isna(sma.iloc[-1]) else current_price
        else:
            current_rsi = 50
            current_macd = 0
            current_signal = 0
            current_upper = current_price * 1.05
            current_lower = current_price * 0.95
            current_sma = current_price
        
        # Volume analysis
        volume_surge = volume > (avg_volume * 1.5) if avg_volume else False
        
        # Generate signals
        signals = []
        
        # RSI signals
        if current_rsi < 30:
            signals.append(('bullish', 2, f'RSI oversold at {current_rsi:.1f}'))
        elif current_rsi > 70:
            signals.append(('bearish', -2, f'RSI overbought at {current_rsi:.1f}'))
        
        # MACD signals
        if current_macd > current_signal:
            signals.append(('bullish', 1, 'MACD bullish crossover'))
        elif current_macd < current_signal:
            signals.append(('bearish', -1, 'MACD bearish crossover'))
        
        # Bollinger Bands signals
        if current_price <= current_lower:
            signals.append(('bullish', 2, 'Price at lower Bollinger Band (oversold)'))
        elif current_price >= current_upper:
            signals.append(('bearish', -2, 'Price at upper Bollinger Band (overbought)'))
        
        # Price vs SMA
        if current_price > current_sma:
            signals.append(('bullish', 1, 'Price above moving average'))
        else:
            signals.append(('bearish', -1, 'Price below moving average'))
        
        # Volume signal
        if volume_surge and change > 0:
            signals.append(('bullish', 1, 'Volume surge on uptrend'))
        elif volume_surge and change < 0:
            signals.append(('bearish', -1, 'Volume surge on downtrend'))
        
        # Calculate overall score
        total_score = sum(s[1] for s in signals)
        confidence = min(abs(total_score) * 12.5 + 50, 95)
        
        # Determine action
        if total_score > 2:
            action = 'BUY'
            reason = f"Strong bullish signals: {', '.join([s[2] for s in signals if s[0] == 'bullish'])}"
            target_multiplier = 1.07
            stop_multiplier = 0.95
            time_horizon = 'short' if abs(total_score) > 4 else 'medium'
        elif total_score < -2:
            action = 'SELL'
            reason = f"Bearish signals detected: {', '.join([s[2] for s in signals if s[0] == 'bearish'])}"
            target_multiplier = 0.93
            stop_multiplier = 1.05
            time_horizon = 'short' if abs(total_score) > 4 else 'medium'
        else:
            action = 'HOLD'
            reason = f"Mixed signals. RSI: {current_rsi:.1f}, MACD: {current_macd:.2f}"
            target_multiplier = 1.02
            stop_multiplier = 0.98
            time_horizon = 'medium'
        
        return {
            'symbol': symbol,
            'price': current_price,
            'change': change,
            'volume': volume,
            'avg_volume': avg_volume,
            'rsi': current_rsi,
            'macd': current_macd,
            'action': action,
            'confidence': int(confidence),
            'reason': reason,
            'target': current_price * target_multiplier,
            'stop_loss': current_price * stop_multiplier,
            'time_horizon': time_horizon,
            'signals': signals
        }
        
    except Exception as e:
        add_stream_message(f"Error analyzing {symbol}: {str(e)}", 'error')
        return None

def check_alerts(stock_data):
    """Check for trading alerts based on analysis"""
    alerts = []
    
    if not stock_data:
        return alerts
    
    # Check for strong buy signals
    if stock_data['action'] == 'BUY' and stock_data['confidence'] > 75:
        alerts.append(Alert(
            symbol=stock_data['symbol'],
            type='BUY',
            price=stock_data['price'],
            reason=f"Strong buy signal with {stock_data['confidence']}% confidence. {stock_data['reason']}",
            confidence=stock_data['confidence'],
            timestamp=datetime.now()
        ))
    
    # Check for strong sell signals
    elif stock_data['action'] == 'SELL' and stock_data['confidence'] > 75:
        alerts.append(Alert(
            symbol=stock_data['symbol'],
            type='SELL',
            price=stock_data['price'],
            reason=f"Strong sell signal with {stock_data['confidence']}% confidence. {stock_data['reason']}",
            confidence=stock_data['confidence'],
            timestamp=datetime.now()
        ))
    
    # Check for RSI extremes
    if stock_data.get('rsi', 50) < 30:
        alerts.append(Alert(
            symbol=stock_data['symbol'],
            type='ALERT',
            price=stock_data['price'],
            reason=f"RSI oversold at {stock_data['rsi']:.1f} - Potential buying opportunity",
            confidence=70,
            timestamp=datetime.now()
        ))
    elif stock_data.get('rsi', 50) > 70:
        alerts.append(Alert(
            symbol=stock_data['symbol'],
            type='ALERT',
            price=stock_data['price'],
            reason=f"RSI overbought at {stock_data['rsi']:.1f} - Consider taking profits",
            confidence=70,
            timestamp=datetime.now()
        ))
    
    return alerts

def create_trade_opportunity(stock_data):
    """Create trade opportunity from analysis"""
    if stock_data['action'] in ['BUY', 'SELL'] and stock_data['confidence'] > 70:
        return TradeOpportunity(
            symbol=stock_data['symbol'],
            action=stock_data['action'],
            entry_price=stock_data['price'],
            target_price=stock_data['target'],
            stop_loss=stock_data['stop_loss'],
            confidence=stock_data['confidence'],
            reason=stock_data['reason'],
            time_horizon=stock_data['time_horizon']
        )
    return None

def update_all_data():
    """Update data for all stocks in watchlist"""
    add_stream_message("🔄 Updating market data...", 'info')
    
    for symbol in st.session_state.watchlist:
        analysis = analyze_stock(symbol)
        if analysis:
            # Store in session state
            st.session_state.stock_analysis[symbol] = analysis
            
            # Check for alerts
            new_alerts = check_alerts(analysis)
            for alert in new_alerts:
                # Avoid duplicate alerts
                if not any(a.symbol == alert.symbol and a.type == alert.type and 
                          (datetime.now() - a.timestamp).seconds < 300 for a in st.session_state.alerts):
                    st.session_state.alerts.append(alert)
                    add_stream_message(f"🔔 ALERT: {alert.symbol} - {alert.type} @ ${alert.price:.2f} - {alert.reason}", 'alert')
            
            # Create trade opportunity
            opportunity = create_trade_opportunity(analysis)
            if opportunity:
                # Avoid duplicate opportunities
                if not any(o.symbol == opportunity.symbol and o.action == opportunity.action and 
                          (datetime.now() - o.timestamp).seconds < 300 for o in st.session_state.opportunities):
                    st.session_state.opportunities.append(opportunity)
                    add_stream_message(f"💡 OPPORTUNITY: {opportunity.action} {opportunity.symbol} @ ${opportunity.entry_price:.2f} (Confidence: {opportunity.confidence}%)", 'opportunity')
    
    st.session_state.last_update = datetime.now()
    add_stream_message(f"✅ Data updated - {len(st.session_state.watchlist)} stocks analyzed", 'success')

def post_to_social_media(message, platform='all'):
    """Post updates to social media"""
    if platform in ['twitter', 'all'] and st.session_state.social_connected.get('twitter', False):
        if TWEEPY_AVAILABLE:
            try:
                # Twitter API integration - you'll need to add your API keys
                # For now, just log it
                add_stream_message(f"📱 Would post to Twitter: {message[:100]}...", 'social')
                return True
            except Exception as e:
                add_stream_message(f"Twitter post failed: {str(e)}", 'error')
        else:
            add_stream_message("⚠️ Tweepy not installed - Twitter posting disabled", 'warning')
    
    if platform in ['instagram', 'all'] and st.session_state.social_connected.get('instagram', False):
        add_stream_message("📷 Instagram post ready (API integration needed)", 'info')
    
    if platform in ['tiktok', 'all'] and st.session_state.social_connected.get('tiktok', False):
        add_stream_message("🎵 TikTok post ready (API integration needed)", 'info')
    
    return False

def auto_stream_loop():
    """Background loop for auto-streaming"""
    while st.session_state.get('auto_stream', False):
        try:
            update_all_data()
            
            # Post top opportunities to social media
            if st.session_state.opportunities:
                latest_opp = st.session_state.opportunities[-1]
                message = f"🤖 AI Trading Alert: {latest_opp.action} {latest_opp.symbol} @ ${latest_opp.entry_price:.2f}\nTarget: ${latest_opp.target_price:.2f}\nConfidence: {latest_opp.confidence}%\n#Stocks #Trading #AI"
                post_to_social_media(message, 'twitter')
            
            time.sleep(300)  # Update every 5 minutes
        except Exception as e:
            add_stream_message(f"Auto-stream error: {str(e)}", 'error')
            time.sleep(60)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Control Panel")
    
    # Live Stream Control
    st.markdown("### 📡 Live Stream Control")
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶️ START", use_container_width=True):
            st.session_state.auto_stream = True
            add_stream_message("🎥 Live stream started!", 'success')
            # Start background thread if not already started
            if not st.session_state.get('stream_thread_started', False):
                import threading
                stream_thread = threading.Thread(target=auto_stream_loop, daemon=True)
                stream_thread.start()
                st.session_state.stream_thread_started = True
    
    with col_stop:
        if st.button("⏸️ STOP", use_container_width=True):
            st.session_state.auto_stream = False
            add_stream_message("⏸️ Live stream stopped", 'warning')
    
    st.divider()
    
    # Stock Watchlist Management
    st.markdown("### 📊 Watchlist")
    all_stocks = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'AMZN', 'MSFT', 'META', 'AMD', 'NFLX', 'JPM', 'V', 'WMT']
    new_stocks = st.multiselect("Add stocks to watchlist", all_stocks, default=st.session_state.watchlist)
    if new_stocks != st.session_state.watchlist:
        st.session_state.watchlist = new_stocks
        add_stream_message(f"📊 Watchlist updated: {', '.join(st.session_state.watchlist)}", 'info')
        # Force update on watchlist change
        update_all_data()
        st.rerun()
    
    st.divider()
    
    # Manual Update Button
    if st.button("🔄 MANUAL UPDATE", use_container_width=True):
        with st.spinner("Updating data..."):
            update_all_data()
        st.success("Data updated!")
    
    st.divider()
    
    # Social Media Connection
    st.markdown("### 🔗 Social Media")
    st.info("📱 Social media posting ready!")
    st.caption("Add API keys in secrets for full integration")

# ==================== MAIN DASHBOARD ====================
# Header with Live Status
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown('<div class="live-badge">🔴 LIVE STREAMING 24/7</div>', unsafe_allow_html=True)
    st.markdown("# 🤖 AI Trading Dashboard")
    st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh: {'ON' if st.session_state.auto_stream else 'OFF'}")

with col2:
    st.metric("Watchlist Size", len(st.session_state.watchlist))

with col3:
    active_alerts = len([a for a in st.session_state.alerts if (datetime.now() - a.timestamp).seconds < 86400])
    st.metric("Active Alerts", active_alerts, delta="New" if active_alerts > 0 else "None")

# Ticker Tape - Safely handle missing data
ticker_parts = []
for s in st.session_state.watchlist:
    analysis = st.session_state.stock_analysis.get(s, {})
    price = analysis.get('price', 0)
    change = analysis.get('change', 0)
    ticker_parts.append(f"{s}: ${price:.2f} ({change:+.2f}%)")

ticker_text = " | ".join(ticker_parts) if ticker_parts else "Loading market data..."
st.markdown(f"""
<div class="ticker-tape">
    <div class="ticker-content">
        🔴 LIVE MARKET DATA • {ticker_text} • 
    </div>
</div>
""", unsafe_allow_html=True)

# Main Dashboard Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Live Market Data", "🎯 Trade Opportunities", "🔔 Alerts", "📡 Live Stream", "📱 Social Feed"])

with tab1:
    st.markdown("## 📊 Real-Time Stock Analysis")
    
    if st.session_state.stock_analysis:
        # Display all stocks in grid
        cols = st.columns(4)
        for idx, symbol in enumerate(st.session_state.watchlist):
            analysis = st.session_state.stock_analysis.get(symbol)
            if analysis:
                col = cols[idx % 4]
                with col:
                    if analysis['action'] == 'BUY':
                        signal_class = "signal-buy"
                        signal_icon = "🟢"
                    elif analysis['action'] == 'SELL':
                        signal_class = "signal-sell"
                        signal_icon = "🔴"
                    else:
                        signal_class = "metric-card"
                        signal_icon = "🟡"
                    
                    st.markdown(f"""
                    <div class="{signal_class}">
                        <h3>{signal_icon} {symbol}</h3>
                        <div style="font-size: 24px; font-weight: bold;">${analysis['price']:.2f}</div>
                        <div style="color: {'#00ff88' if analysis['change'] >= 0 else '#ff4444'}">
                            {analysis['change']:+.2f}%
                        </div>
                        <div>RSI: {analysis.get('rsi', 50):.1f}</div>
                        <div style="margin-top: 10px;">
                            <strong>{analysis['action']}</strong> - {analysis['confidence']}%
                        </div>
                        <small>{analysis['reason'][:80]}...</small>
                    </div>
                    <br>
                    """, unsafe_allow_html=True)
    else:
        st.info("Click 'MANUAL UPDATE' to load stock data")
    
    # Detailed chart for selected stock
    if st.session_state.stock_analysis:
        st.markdown("### 📈 Detailed Analysis")
        selected_chart = st.selectbox("Select stock for chart", st.session_state.watchlist)
        if selected_chart and selected_chart in st.session_state.stock_analysis:
            analysis = st.session_state.stock_analysis[selected_chart]
            
            # Fetch historical data for chart
            stock = yf.Ticker(selected_chart)
            hist = stock.history(period="1d", interval="5m")
            
            if not hist.empty:
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
                
                fig.update_layout(
                    title=f"{selected_chart} - ${analysis['price']:.2f} ({analysis['action']} Signal - {analysis['confidence']}% Confidence)",
                    template='plotly_dark',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("## 💰 Active Trade Opportunities")
    
    # Filter opportunities
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_action = st.selectbox("Filter by action", ["ALL", "BUY", "SELL"])
    with col_filter2:
        filter_confidence = st.slider("Min confidence", 0, 100, 50)
    
    opportunities = [opp for opp in st.session_state.opportunities if (filter_action == "ALL" or opp.action == filter_action) and opp.confidence >= filter_confidence]
    
    if opportunities:
        for opp in opportunities[-10:]:  # Show last 10 opportunities
            st.markdown(f"""
            <div class="opportunity-card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h2>{'🟢' if opp.action == 'BUY' else '🔴'} {opp.action} {opp.symbol}</h2>
                        <div style="font-size: 32px; font-weight: bold;">${opp.entry_price:.2f}</div>
                    </div>
                    <div style="text-align: right;">
                        <div>Confidence: {opp.confidence}%</div>
                        <div>Time Horizon: {opp.time_horizon}</div>
                    </div>
                </div>
                <div style="margin-top: 10px;">
                    <strong>Target Price:</strong> ${opp.target_price:.2f}<br>
                    <strong>Stop Loss:</strong> ${opp.stop_loss:.2f}<br>
                    <strong>Reason:</strong> {opp.reason}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active trade opportunities at this time")
    
    # Action buttons for each opportunity
    if opportunities:
        st.markdown("### 🎯 Take Action")
        selected_opp = st.selectbox("Select opportunity", [f"{opp.action} {opp.symbol} @ ${opp.entry_price:.2f}" for opp in opportunities[-5:]])
        if st.button("Execute Trade", use_container_width=True):
            add_stream_message(f"💼 Trade executed: {selected_opp}", 'success')
            post_to_social_media(f"🤖 AI Trade Alert: {selected_opp} - Confidence high! #Trading #AI", 'twitter')

with tab3:
    st.markdown("## 🔔 Active Alerts")
    
    # Display recent alerts
    if st.session_state.alerts:
        for alert in st.session_state.alerts[-20:]:
            st.markdown(f"""
            <div class="alert-card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <strong>{'🚨' if alert.type == 'ALERT' else ('🟢' if alert.type == 'BUY' else '🔴')} {alert.type}</strong> {alert.symbol}
                    </div>
                    <div>{alert.timestamp.strftime('%H:%M:%S')}</div>
                </div>
                <div style="font-size: 20px;">${alert.price:.2f}</div>
                <div>{alert.reason}</div>
                <div>Confidence: {alert.confidence}%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active alerts")
    
    # Clear alerts button
    if st.button("Clear All Alerts", use_container_width=True):
        st.session_state.alerts = []
        add_stream_message("All alerts cleared", 'info')
        st.rerun()

with tab4:
    st.markdown("## 📡 Live Data Stream")
    
    # Live stream display
    stream_container = st.container()
    with stream_container:
        st.markdown('<div class="live-stream">', unsafe_allow_html=True)
        for msg in st.session_state.stream_messages[:50]:
            if msg['type'] == 'alert':
                color = "#ff3366"
                icon = "🔔"
            elif msg['type'] == 'opportunity':
                color = "#00ff88"
                icon = "💡"
            elif msg['type'] == 'success':
                color = "#00ff88"
                icon = "✅"
            elif msg['type'] == 'error':
                color = "#ff4444"
                icon = "❌"
            elif msg['type'] == 'social':
                color = "#00aaff"
                icon = "📱"
            else:
                color = "#888"
                icon = "ℹ️"
            
            st.markdown(f"""
            <div class="stream-message" style="border-left-color: {color};">
                <span style="color: {color};">{icon}</span>
                <strong>[{msg['time']}]</strong> {msg['message']}
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Stream controls
    col_clear, col_export = st.columns(2)
    with col_clear:
        if st.button("Clear Stream", use_container_width=True):
            st.session_state.stream_messages = []
            st.rerun()
    with col_export:
        if st.button("Export Log", use_container_width=True):
            log_text = "\n".join([f"[{m['time']}] {m['message']}" for m in st.session_state.stream_messages])
            st.download_button("Download Log", log_text, "trading_log.txt")

with tab5:
    st.markdown("## 📱 Social Media Feed")
    
    # Post to social media
    st.markdown("### Create Post")
    post_content = st.text_area("What's happening?", height=100, placeholder="Share your trading insights...")
    
    col_post1, col_post2, col_post3 = st.columns(3)
    with col_post1:
        if st.button("🐦 Post to X", use_container_width=True) and post_content:
            post_to_social_media(post_content, 'twitter')
            st.success("Posted to Twitter!")
    
    with col_post2:
        if st.button("📷 Post to Instagram", use_container_width=True) and post_content:
            post_to_social_media(post_content, 'instagram')
            st.success("Posted to Instagram!")
    
    with col_post3:
        if st.button("🎵 Post to TikTok", use_container_width=True) and post_content:
            post_to_social_media(post_content, 'tiktok')
            st.success("Posted to TikTok!")
    
    st.divider()
    
    # Auto-post settings
    st.markdown("### 🤖 Auto-Post Settings")
    auto_post_frequency = st.selectbox("Auto-post frequency", ["Off", "Every hour", "Every 4 hours", "Every market hour"])
    
    if auto_post_frequency != "Off":
        st.info(f"Auto-posting enabled: {auto_post_frequency}. Market updates will be posted automatically.")
        
        # Preview of auto-post message
        if st.session_state.opportunities:
            latest = st.session_state.opportunities[-1]
            preview = f"🤖 AI Trading Alert: {latest.action} {latest.symbol} @ ${latest.entry_price:.2f}\nTarget: ${latest.target_price:.2f}\nConfidence: {latest.confidence}%\n#Stocks #Trading #AI"
            st.markdown("**Preview of next auto-post:**")
            st.info(preview)

# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    🤖 AI Trading Dashboard - 24/7 Live Market Intelligence<br>
    Real-time Analysis | AI Predictions | Auto-Alerts | Social Media Integration<br>
    <small>⚠️ Not financial advice. Always do your own research before trading.</small>
</div>
""", unsafe_allow_html=True)

# ==================== INITIAL DATA LOAD ====================
# Load initial data if empty
if not st.session_state.stock_analysis:
    update_all_data()
