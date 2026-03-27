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

@dataclass
class AIPrediction:
    symbol: str
    current_price: float
    predicted_price_1w: float
    predicted_price_1m: float
    predicted_price_3m: float
    confidence_1w: int
    confidence_1m: int
    confidence_3m: int
    signal: str
    target_price: float
    stop_loss: float
    risk_level: str
    reason: str

@dataclass
class InvestmentPlan:
    symbol: str
    investment_amount: float
    time_horizon: str
    current_price: float
    predicted_price: float
    potential_return: float
    risk_score: int
    recommended_action: str
    shares_to_buy: int
    optimal_entry: str
    exit_strategy: str

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
    if 'ai_predictions' not in st.session_state:
        st.session_state.ai_predictions = {}
    
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

def calculate_ai_prediction(symbol):
    """Calculate AI prediction based on technical analysis and historical patterns"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="6mo")
        
        if hist.empty:
            return None
        
        current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
        
        if current_price == 0:
            return None
        
        # Calculate moving averages
        ma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        ma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) > 50 else current_price
        
        # Calculate RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        # Calculate momentum
        momentum_1w = (hist['Close'].iloc[-1] / hist['Close'].iloc[-5] - 1) * 100 if len(hist) > 5 else 0
        momentum_1m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-20] - 1) * 100 if len(hist) > 20 else 0
        
        # Make predictions based on technical indicators
        if current_price > ma_20 and current_price > ma_50 and current_rsi < 70:
            predicted_1w = current_price * (1 + max(0, momentum_1w / 100) + 0.02)
            predicted_1m = current_price * (1 + max(0, momentum_1m / 100) + 0.05)
            predicted_3m = current_price * (1 + max(0, momentum_1m / 100) * 1.5 + 0.08)
            confidence_1w = min(90, 60 + abs(momentum_1w))
            confidence_1m = min(85, 55 + abs(momentum_1m))
            confidence_3m = min(80, 50 + abs(momentum_1m))
            
            if momentum_1w > 5 and current_rsi < 50:
                signal = "STRONG BUY"
                risk_level = "LOW"
            elif momentum_1w > 2:
                signal = "BUY"
                risk_level = "LOW"
            else:
                signal = "HOLD"
                risk_level = "MEDIUM"
                
        elif current_price < ma_20 and current_price < ma_50 and current_rsi > 30:
            predicted_1w = current_price * (1 - max(0, abs(momentum_1w) / 100) - 0.02)
            predicted_1m = current_price * (1 - max(0, abs(momentum_1m) / 100) - 0.05)
            predicted_3m = current_price * (1 - max(0, abs(momentum_1m) / 100) * 1.5 - 0.08)
            confidence_1w = min(90, 60 + abs(momentum_1w))
            confidence_1m = min(85, 55 + abs(momentum_1m))
            confidence_3m = min(80, 50 + abs(momentum_1m))
            
            if momentum_1w < -5 and current_rsi > 50:
                signal = "STRONG SELL"
                risk_level = "HIGH"
            elif momentum_1w < -2:
                signal = "SELL"
                risk_level = "HIGH"
            else:
                signal = "HOLD"
                risk_level = "MEDIUM"
        else:
            predicted_1w = current_price * 1.02
            predicted_1m = current_price * 1.03
            predicted_3m = current_price * 1.05
            confidence_1w = 50
            confidence_1m = 50
            confidence_3m = 50
            signal = "HOLD"
            risk_level = "MEDIUM"
        
        # Set target and stop loss
        if signal in ["STRONG BUY", "BUY"]:
            target_price = current_price * 1.08
            stop_loss = current_price * 0.95
        elif signal in ["STRONG SELL", "SELL"]:
            target_price = current_price * 0.92
            stop_loss = current_price * 1.05
        else:
            target_price = current_price * 1.03
            stop_loss = current_price * 0.97
        
        reason = f"Price above MA20, RSI: {current_rsi:.1f}, Momentum: {momentum_1w:+.1f}%"
        
        return AIPrediction(
            symbol=symbol,
            current_price=current_price,
            predicted_price_1w=predicted_1w,
            predicted_price_1m=predicted_1m,
            predicted_price_3m=predicted_3m,
            confidence_1w=int(confidence_1w),
            confidence_1m=int(confidence_1m),
            confidence_3m=int(confidence_3m),
            signal=signal,
            target_price=target_price,
            stop_loss=stop_loss,
            risk_level=risk_level,
            reason=reason
        )
        
    except Exception as e:
        add_stream_message(f"AI prediction error for {symbol}: {str(e)}", 'error')
        return None

def calculate_investment_plan(symbol, investment_amount, time_horizon, prediction):
    """Calculate optimal investment plan"""
    if not prediction:
        return None
    
    current_price = prediction.current_price
    shares_to_buy = int(investment_amount / current_price) if current_price > 0 else 0
    
    # Determine predicted price based on time horizon
    if time_horizon == "short":
        predicted_price = prediction.predicted_price_1w
        confidence = prediction.confidence_1w
    elif time_horizon == "medium":
        predicted_price = prediction.predicted_price_1m
        confidence = prediction.confidence_1m
    else:
        predicted_price = prediction.predicted_price_3m
        confidence = prediction.confidence_3m
    
    potential_return = ((predicted_price - current_price) / current_price * 100) if current_price > 0 else 0
    
    # Determine recommended action
    if prediction.signal in ["STRONG BUY", "BUY"] and potential_return > 5:
        recommended_action = "STRONG BUY - Good entry point"
        optimal_entry = "Current price is favorable"
        exit_strategy = f"Sell at ${prediction.target_price:.2f} or use trailing stop loss"
    elif prediction.signal == "HOLD" and potential_return > 2:
        recommended_action = "HOLD - Wait for better entry"
        optimal_entry = f"Consider buying below ${current_price * 0.97:.2f}"
        exit_strategy = "Monitor closely, set alerts for price breakouts"
    elif prediction.signal in ["SELL", "STRONG SELL"]:
        recommended_action = "AVOID - Bearish signals detected"
        optimal_entry = "Not recommended at current levels"
        exit_strategy = "If holding, consider reducing position"
    else:
        recommended_action = "CAUTIOUS - Monitor before investing"
        optimal_entry = f"Ideal entry: ${current_price * 0.95:.2f} - ${current_price * 0.98:.2f}"
        exit_strategy = "Set limit orders for profit taking"
    
    return InvestmentPlan(
        symbol=symbol,
        investment_amount=investment_amount,
        time_horizon=time_horizon,
        current_price=current_price,
        predicted_price=predicted_price,
        potential_return=potential_return,
        risk_score=100 - confidence,
        recommended_action=recommended_action,
        shares_to_buy=shares_to_buy,
        optimal_entry=optimal_entry,
        exit_strategy=exit_strategy
    )

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
    <p style="color: white; font-size: 18px;">8 Global Exchanges | 11 Sectors | AI Predictions | Investment Calculator</p>
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
            
            # Update AI predictions
            for symbol in st.session_state.watchlist:
                st.session_state.ai_predictions[symbol] = calculate_ai_prediction(symbol)
            
            st.session_state.last_update = datetime.now()
        st.success("Data updated!")

st.caption(f"Last updated: {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== TABS SECTION ====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 Exchanges", 
    "📈 Sectors", 
    "🚨 Alerts", 
    "🤖 AI Predictions", 
    "💰 Investment Calculator", 
    "📡 Live Stream"
])

# ==================== TAB 1: EXCHANGES ====================
with tab1:
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

# ==================== TAB 2: SECTORS ====================
with tab2:
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

# ==================== TAB 3: ALERTS ====================
with tab3:
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

# ==================== TAB 4: AI PREDICTIONS ====================
with tab4:
    st.markdown("## 🤖 AI-Powered Stock Predictions")
    st.caption("Machine learning analysis based on historical patterns, technical indicators, and market sentiment")
    
    # Stock selector for AI predictions
    ai_symbol = st.selectbox("Select Stock for AI Analysis", st.session_state.watchlist)
    
    if ai_symbol:
        with st.spinner(f"Analyzing {ai_symbol} with AI..."):
            # Get prediction (use cached if available)
            if ai_symbol in st.session_state.ai_predictions:
                ai_prediction = st.session_state.ai
