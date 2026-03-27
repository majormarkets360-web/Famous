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
from sklearn.model_selection import train_test_split
import joblib

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

warnings.filterwarnings('ignore')

# ==================== DATA CLASSES ====================
@dataclass
class AIPrediction:
    symbol: str
    current_price: float
    predicted_price_1d: float
    predicted_price_1w: float
    predicted_price_1m: float
    confidence_1d: float
    confidence_1w: float
    confidence_1m: float
    buy_signal: str
    entry_price: float
    target_price: float
    stop_loss: float
    risk_score: int
    reason: str
    technical_signals: Dict
    sentiment_score: float

@dataclass
class TradingAlert:
    symbol: str
    alert_type: str
    price: float
    message: str
    confidence: int
    timestamp: datetime
    action_required: bool

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="AI Trading Dashboard - Live Predictions",
    page_icon="🚀",
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
    if 'historical_data' not in st.session_state:
        st.session_state.historical_data = {}
    if 'stream_messages' not in st.session_state:
        st.session_state.stream_messages = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    if 'auto_stream' not in st.session_state:
        st.session_state.auto_stream = False
    if 'social_connected' not in st.session_state:
        st.session_state.social_connected = {'twitter': False, 'youtube': False, 'facebook': False, 'tiktok': False}
    if 'user_portfolio' not in st.session_state:
        st.session_state.user_portfolio = {}
    if 'prediction_models' not in st.session_state:
        st.session_state.prediction_models = {}
    if 'leaderboard' not in st.session_state:
        st.session_state.leaderboard = []
    
    if SOCIAL_STREAMER_AVAILABLE and 'social_streamer' not in st.session_state:
        st.session_state.social_streamer = SocialMediaStreamer()

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

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ==================== AI PREDICTION ENGINE ====================

class AIStockPredictor:
    """Advanced AI Stock Prediction Engine"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def train_model(self, symbol, historical_data):
        """Train ML model for a specific stock"""
        try:
            df = historical_data.copy()
            
            # Technical indicators
            df['returns'] = df['Close'].pct_change()
            df['volume_change'] = df['Volume'].pct_change()
            df['ma_5'] = df['Close'].rolling(5).mean()
            df['ma_10'] = df['Close'].rolling(10).mean()
            df['ma_20'] = df['Close'].rolling(20).mean()
            df['rsi'] = self.calculate_rsi(df['Close'])
            df['volatility'] = df['returns'].rolling(20).std()
            
            # Price targets
            df['target_1d'] = df['Close'].shift(-1)
            df['target_1w'] = df['Close'].shift(-5)
            df['target_1m'] = df['Close'].shift(-20)
            
            df = df.dropna()
            
            feature_cols = ['returns', 'volume_change', 'ma_5', 'ma_10', 'ma_20', 'rsi', 'volatility']
            
            X = df[feature_cols].values
            y_1d = df['target_1d'].values
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=5)
            model.fit(X_scaled, y_1d)
            
            self.models[symbol] = {
                'model': model,
                'scaler': scaler,
                'feature_cols': feature_cols
            }
            
            return True, "Model trained successfully"
        except Exception as e:
            return False, str(e)
    
    def predict(self, symbol, current_data, historical_data):
        """Make prediction for a stock"""
        if symbol not in self.models:
            return None
        
        try:
            model_data = self.models[symbol]
            df = historical_data.tail(10).copy()
            
            df['returns'] = df['Close'].pct_change()
            df['volume_change'] = df['Volume'].pct_change()
            df['ma_5'] = df['Close'].rolling(5).mean()
            df['ma_10'] = df['Close'].rolling(10).mean()
            df['ma_20'] = df['Close'].rolling(20).mean()
            df['rsi'] = self.calculate_rsi(df['Close'])
            df['volatility'] = df['returns'].rolling(20).std()
            
            latest = df.iloc[-1]
            features = np.array([[latest[col] for col in model_data['feature_cols']]])
            features_scaled = model_data['scaler'].transform(features)
            
            pred = model_data['model'].predict(features_scaled)[0]
            confidence = min(95, max(50, 100 - abs((pred - current_data['price']) / current_data['price'] * 100)))
            
            return {
                '1d': pred,
                'conf_1d': confidence
            }
        except Exception as e:
            return None

# Initialize predictor
if 'predictor' not in st.session_state:
    st.session_state.predictor = AIStockPredictor()

def analyze_stock_advanced(symbol):
    """Comprehensive stock analysis"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="3mo")
        
        if hist.empty:
            return None
        
        current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        change = ((current_price - info.get('regularMarketPreviousClose', current_price)) / 
                  info.get('regularMarketPreviousClose', current_price) * 100)
        
        if symbol not in st.session_state.predictor.models:
            success, msg = st.session_state.predictor.train_model(symbol, hist)
        
        predictions = st.session_state.predictor.predict(symbol, {'price': current_price}, hist)
        
        # Calculate technical signals
        rsi = calculate_rsi(hist['Close'])
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        # Generate signal
        if current_rsi < 30:
            signal = "STRONG BUY"
            confidence = 85
            reason = "RSI indicates oversold conditions"
        elif current_rsi < 45:
            signal = "BUY"
            confidence = 70
            reason = "Positive momentum detected"
        elif current_rsi > 70:
            signal = "STRONG SELL"
            confidence = 85
            reason = "RSI indicates overbought conditions"
        elif current_rsi > 55:
            signal = "SELL"
            confidence = 70
            reason = "Bearish signals detected"
        else:
            signal = "HOLD"
            confidence = 50
            reason = "Neutral market conditions"
        
        # Calculate targets
        if signal in ["STRONG BUY", "BUY"]:
            target_price = current_price * 1.05
            stop_loss = current_price * 0.97
        elif signal in ["STRONG SELL", "SELL"]:
            target_price = current_price * 0.95
            stop_loss = current_price * 1.03
        else:
            target_price = current_price * 1.02
            stop_loss = current_price * 0.98
        
        risk_score = 30 if signal in ["STRONG BUY", "BUY"] else 70 if signal in ["STRONG SELL", "SELL"] else 50
        
        ai_prediction = AIPrediction(
            symbol=symbol,
            current_price=current_price,
            predicted_price_1d=predictions['1d'] if predictions else current_price,
            predicted_price_1w=predictions['1d'] * 1.02 if predictions else current_price,
            predicted_price_1m=predictions['1d'] * 1.05 if predictions else current_price,
            confidence_1d=predictions['conf_1d'] if predictions else 50,
            confidence_1w=50,
            confidence_1m=50,
            buy_signal=signal,
            entry_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            risk_score=risk_score,
            reason=reason,
            technical_signals={'rsi': current_rsi},
            sentiment_score=0
        )
        
        st.session_state.predictions[symbol] = ai_prediction
        
        if signal in ["STRONG BUY", "BUY"] and confidence > 70:
            alert = TradingAlert(
                symbol=symbol,
                alert_type='BUY',
                price=current_price,
                message=f"Strong {signal} signal! Target: ${target_price:.2f}",
                confidence=confidence,
                timestamp=datetime.now(),
                action_required=True
            )
            st.session_state.alerts.append(alert)
            add_stream_message(f"🚨 {signal} ALERT: {symbol} @ ${current_price:.2f}", 'alert')
        
        return ai_prediction
        
    except Exception as e:
        add_stream_message(f"Error analyzing {symbol}: {str(e)}", 'error')
        return None

def create_3d_price_chart(symbol, historical_data, predictions):
    """Create stunning price chart"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=historical_data.index,
        y=historical_data['Close'],
        mode='lines',
        name='Historical Price',
        line=dict(color='#00ff88', width=3)
    ))
    
    fig.update_layout(
        title=f'{symbol} - Price Chart with AI Predictions',
        template='plotly_dark',
        height=500,
        xaxis_title='Date',
        yaxis_title='Price ($)'
    )
    
    return fig

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Control Panel")
    
    # Live Stream Control
    st.markdown("### 📡 Live Stream")
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶️ START", use_container_width=True):
            st.session_state.auto_stream = True
            add_stream_message("🎥 Live stream started!", 'success')
    with col_stop:
        if st.button("⏸️ STOP", use_container_width=True):
            st.session_state.auto_stream = False
            add_stream_message("⏸️ Live stream stopped", 'warning')
    
    st.divider()
    
    # Stock Watchlist
    st.markdown("### 📊 Watchlist")
    all_stocks = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'AMZN', 'MSFT', 'META', 'AMD']
    new_stocks = st.multiselect("Select stocks", all_stocks, default=st.session_state.watchlist)
    if new_stocks != st.session_state.watchlist:
        st.session_state.watchlist = new_stocks
        st.rerun()
    
    st.divider()
    
    # Manual Update
    if st.button("🔄 UPDATE DATA", use_container_width=True):
        with st.spinner("Analyzing stocks with AI..."):
            for symbol in st.session_state.watchlist:
                analyze_stock_advanced(symbol)
        st.success("Data updated!")
    
    st.divider()
    
    # Social Media Connection
    if SOCIAL_STREAMER_AVAILABLE:
        st.markdown("### 🌐 Social Media")
        if st.button("📢 POST LATEST ALERT", use_container_width=True):
            if st.session_state.alerts:
                latest = st.session_state.alerts[-1]
                message = f"🤖 AI Trading Alert: {latest.alert_type} {latest.symbol} @ ${latest.price:.2f}\n{latest.message}\n#Stocks #Trading #AI"
                st.success(f"Alert ready to post: {message[:100]}...")

# ==================== MAIN DASHBOARD ====================

# Header
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 20px; margin-bottom: 2rem; text-align: center;">
    <h1 style="color: white;">🚀 AI Trading Intelligence Dashboard</h1>
    <p style="color: white; font-size: 18px;">Real-time AI Predictions | Smart Alerts | Live Streaming</p>
</div>
""", unsafe_allow_html=True)

# Key Metrics Row
col1, col2, col3, col4 = st.columns(4)

buy_signals = sum(1 for p in st.session_state.predictions.values() if "BUY" in p.buy_signal)
sell_signals = sum(1 for p in st.session_state.predictions.values() if "SELL" in p.buy_signal)
avg_confidence = np.mean([p.confidence_1d for p in st.session_state.predictions.values()]) if st.session_state.predictions else 0
avg_risk = np.mean([p.risk_score for p in st.session_state.predictions.values()]) if st.session_state.predictions else 0

with col1:
    st.metric("📈 Buy Signals", buy_signals)
with col2:
    st.metric("📉 Sell Signals", sell_signals)
with col3:
    st.metric("🎯 AI Confidence", f"{avg_confidence:.0f}%")
with col4:
    st.metric("⚠️ Risk Score", f"{avg_risk:.0f}/100")

st.divider()

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 AI Predictions",
    "📊 Charts & Analysis",
    "🎯 Trading Opportunities",
    "📡 Live Stream"
])

with tab1:
    st.markdown("## 🤖 AI-Powered Stock Predictions")
    
    # Display predictions in grid
    cols = st.columns(3)
    for idx, symbol in enumerate(st.session_state.watchlist):
        if symbol in st.session_state.predictions:
            pred = st.session_state.predictions[symbol]
            col = cols[idx % 3]
            
            with col:
                # Signal badge
                if pred.buy_signal == "STRONG BUY":
                    badge_color = "#00ff88"
                    badge_text = "🔥 STRONG BUY"
                elif pred.buy_signal == "BUY":
                    badge_color = "#88ff00"
                    badge_text = "✅ BUY"
                elif pred.buy_signal == "STRONG SELL":
                    badge_color = "#ff3366"
                    badge_text = "🔴 STRONG SELL"
                elif pred.buy_signal == "SELL":
                    badge_color = "#ff6644"
                    badge_text = "⚠️ SELL"
                else:
                    badge_color = "#ffaa00"
                    badge_text = "⏸️ HOLD"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1e1e1e, #2d2d2d); border-radius: 15px; padding: 20px; margin: 10px 0; border-left: 4px solid {badge_color};">
                    <h3>{symbol}</h3>
                    <div style="font-size: 28px; font-weight: bold;">${pred.current_price:.2f}</div>
                    <div style="margin: 10px 0;">
                        <span style="background: {badge_color}; color: black; padding: 5px 10px; border-radius: 10px; font-weight: bold;">
                            {badge_text}
                        </span>
                    </div>
                    <div>Confidence: {pred.confidence_1d}%</div>
                    <div>Target: ${pred.target_price:.2f}</div>
                    <div>Stop Loss: ${pred.stop_loss:.2f}</div>
                    <div style="font-size: 12px; color: #888; margin-top: 10px;">{pred.reason}</div>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.markdown("## 📊 Interactive Charts")
    
    selected_chart = st.selectbox("Select stock", st.session_state.watchlist)
    if selected_chart:
        stock = yf.Ticker(selected_chart)
        hist = stock.history(period="1mo")
        
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
                title=f"{selected_chart} - Price Chart",
                template='plotly_dark',
                height=500,
                xaxis_title='Date',
                yaxis_title='Price ($)'
            )
            
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("## 🎯 Active Trading Opportunities")
    
    if st.session_state.alerts:
        for alert in st.session_state.alerts[-10:]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ff3366, #ff0066); padding: 15px; border-radius: 10px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <strong>{alert.alert_type}</strong> {alert.symbol}
                    </div>
                    <div>{alert.timestamp.strftime('%H:%M:%S')}</div>
                </div>
                <div style="font-size: 20px;">${alert.price:.2f}</div>
                <div>{alert.message}</div>
                <div>Confidence: {alert.confidence}%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active alerts. Click UPDATE DATA to get predictions.")

with tab4:
    st.markdown("## 📡 Live Data Stream")
    
    stream_container = st.container()
    with stream_container:
        for msg in st.session_state.stream_messages[:50]:
            if msg['type'] == 'alert':
                color = "#ff3366"
                icon = "🔔"
            elif msg['type'] == 'success':
                color = "#00ff88"
                icon = "✅"
            elif msg['type'] == 'error':
                color = "#ff4444"
                icon = "❌"
            else:
                color = "#888"
                icon = "ℹ️"
            
            st.markdown(f"""
            <div style="padding: 5px; border-bottom: 1px solid #333;">
                <span style="color: {color};">{icon}</span>
                <strong>[{msg['time']}]</strong> {msg['message']}
            </div>
            """, unsafe_allow_html=True)
    
    if st.button("Clear Stream", use_container_width=True):
        st.session_state.stream_messages = []
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    🤖 AI Trading Dashboard - 24/7 Live Market Intelligence<br>
    Real-time Analysis | AI Predictions | Auto-Alerts<br>
    <small>⚠️ Not financial advice. Always do your own research before trading.</small>
</div>
""", unsafe_allow_html=True)

# Initial data load
if not st.session_state.predictions:
    for symbol in st.session_state.watchlist:
        analyze_stock_advanced(symbol)
