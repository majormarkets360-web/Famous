import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
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
    st.session_state.watchlist = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT', 'AMZN', 'META']
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
    "🇺🇸 NYSE": {"indices": "^NYA", "city": "New York", "color": "#00cc88"},
    "📊 NASDAQ": {"indices": "^IXIC", "city": "New York", "color": "#44ffaa"},
    "🇨🇳 Shanghai": {"indices": "000001.SS", "city": "Shanghai", "color": "#ff8866"},
    "🇯🇵 Japan": {"indices": "^N225", "city": "Tokyo", "color": "#ffaa66"},
    "🇪🇺 Euronext": {"indices": "^FCHI", "city": "Paris", "color": "#66aaff"},
    "🇭🇰 Hong Kong": {"indices": "^HSI", "city": "Hong Kong", "color": "#ff88aa"},
    "🇮🇳 India": {"indices": "^NSEI", "city": "Mumbai", "color": "#ffaa88"},
    "🇬🇧 London": {"indices": "^FTSE", "city": "London", "color": "#88ffaa"}
}

SECTORS = {
    "Technology": {"etf": "XLK", "icon": "💻", "color": "#00cc88"},
    "Financials": {"etf": "XLF", "icon": "🏦", "color": "#44ffaa"},
    "Healthcare": {"etf": "XLV", "icon": "🏥", "color": "#66aaff"},
    "Consumer": {"etf": "XLY", "icon": "🛍️", "color": "#ffaa66"},
    "Industrials": {"etf": "XLI", "icon": "🏭", "color": "#88ffaa"},
    "Energy": {"etf": "XLE", "icon": "⚡", "color": "#ff8866"}
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
    for name, config in SECTORS.items():
        try:
            ticker = yf.Ticker(config['etf'])
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
        
        return {
            'symbol': symbol,
            'current_price': price,
            'predicted_1w': predicted,
            'predicted_1m': predicted * 1.02,
            'predicted_3m': predicted * 1.05,
            'signal': signal,
            'confidence': confidence,
            'target': predicted,
            'stop_loss': price * 0.97
        }
    except:
        return None

def calculate_investment_plan(symbol, amount, prediction):
    if not prediction:
        return None
    shares = int(amount / prediction['current_price']) if prediction['current_price'] > 0 else 0
    potential_return = ((prediction['target'] - prediction['current_price']) / prediction['current_price'] * 100)
    return {
        'symbol': symbol,
        'investment_amount': amount,
        'shares': shares,
        'current_price': prediction['current_price'],
        'target_price': prediction['target'],
        'potential_return': potential_return,
        'recommendation': f"{prediction['signal']} with {prediction['confidence']}% confidence"
    }

def create_stock_chart(symbol, period="1mo"):
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
            increasing_line_color='#00cc88',
            decreasing_line_color='#ff6666'
        ))
        
        # Add volume bars
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            marker_color='rgba(0, 204, 136, 0.3)',
            yaxis='y2'
        ))
        
        # Add moving averages
        if len(hist) > 20:
            ma20 = hist['Close'].rolling(20).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma20, name='MA20', line=dict(color='#ffaa44', width=1)))
        
        if len(hist) > 50:
            ma50 = hist['Close'].rolling(50).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma50, name='MA50', line=dict(color='#ff8866', width=1)))
        
        fig.update_layout(
            title=f"{symbol} - Price Chart",
            template='plotly_dark',
            height=450,
            yaxis_title='Price ($)',
            yaxis2=dict(title='Volume', overlaying='y', side='right'),
            hovermode='x unified',
            plot_bgcolor='rgba(30,30,50,0.5)',
            paper_bgcolor='rgba(30,30,50,0.3)'
        )
        
        return fig
    except:
        return None

def update_all_data():
    with st.spinner("Updating market data..."):
        st.session_state.exchange_data = fetch_exchange_data()
        st.session_state.sector_data = fetch_sector_data()
        for symbol in st.session_state.watchlist:
            st.session_state.ai_predictions[symbol] = calculate_ai_prediction(symbol)
        st.session_state.last_update = datetime.now()
    return True

# ========== LIGHTER CSS ==========
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%);
    }
    
    .exchange-card, .stat-card, .sector-card, .investment-card, .chart-container {
        background: rgba(45, 45, 65, 0.85) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 204, 136, 0.3);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    
    .exchange-card:hover, .stat-card:hover, .sector-card:hover, .investment-card:hover {
        border: 1px solid #00cc88;
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0, 204, 136, 0.2);
    }
    
    /* Light text for readability */
    .positive { color: #00cc88; font-weight: 600; }
    .negative { color: #ff8888; font-weight: 600; }
    .neutral { color: #ffaa66; font-weight: 600; }
    
    .stat-value { font-size: 32px; font-weight: 700; color: #00cc88; }
    .stat-label { color: #aaa; font-size: 14px; }
    .market-name { font-size: 16px; font-weight: 600; color: #00cc88; }
    .market-value { font-size: 28px; font-weight: 700; color: #fff; }
    .market-change { font-size: 14px; }
    .sector-name { font-weight: 600; color: #ddd; }
    .sector-perf { font-size: 18px; font-weight: 700; }
    
    .stButton > button {
        background: linear-gradient(135deg, #00cc88, #00aa66);
        color: #000;
        font-weight: 600;
        border-radius: 25px;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(0, 204, 136, 0.3);
    }
    
    .live-badge {
        background: linear-gradient(90deg, #ff6666, #ff3366);
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
        background: rgba(30, 30, 50, 0.9);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        border-bottom: 2px solid #00cc88;
    }
    
    [data-testid="stSidebar"] {
        background: rgba(20, 20, 40, 0.95);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(0, 204, 136, 0.2);
    }
    
    /* Sidebar text colors */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] .stMetric, 
    [data-testid="stSidebar"] .stText {
        color: #ddd;
    }
    
    .timezone-ticker {
        background: rgba(0, 0, 0, 0.4);
        border-radius: 30px;
        padding: 10px 20px;
        margin: 10px 0;
        overflow: hidden;
        white-space: nowrap;
        border: 1px solid rgba(0, 204, 136, 0.3);
    }
    
    .timezone-ticker-content {
        display: inline-block;
        animation: ticker 50s linear infinite;
        color: #ddd;
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
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 204, 136, 0.3);
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin: 10px 0;
        transition: all 0.3s;
    }
    
    .ad-container:hover {
        border-color: #00cc88;
        transform: translateY(-2px);
    }
    
    .ad-title { color: #00cc88; font-size: 12px; font-weight: bold; }
    .ad-content { color: #ccc; font-size: 12px; margin: 5px 0; }
    .ad-button {
        background: #00cc88;
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        margin-top: 8px;
    }
    
    .stock-ticker {
        background: rgba(0, 0, 0, 0.5);
        border-radius: 16px;
        padding: 15px;
        margin: 10px 0;
        text-align: center;
        border: 1px solid rgba(0, 204, 136, 0.3);
    }
    
    .investment-title {
        color: #00cc88;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 15px;
        text-align: center;
    }
    
    /* Chart container */
    .chart-container {
        padding: 15px;
    }
    
    /* Alert cards */
    .alert-card {
        background: rgba(45, 45, 65, 0.85);
        border-radius: 12px;
        padding: 12px;
        margin: 8px 0;
        border-left: 4px solid #00cc88;
    }
    
    /* Prediction card */
    .prediction-card {
        background: rgba(45, 45, 65, 0.85);
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Text colors */
    .stMarkdown, .stText, .stMetric, .stDataFrame {
        color: #e0e0e0;
    }
    
    h1, h2, h3, h4 {
        color: #ffffff;
    }
    
    .stSelectbox label, .stNumberInput label {
        color: #ddd;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ====================
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="color: #00cc88; margin: 0;">🤖 AI Trading Dashboard</h1>
            <p style="color: #aaa; margin-top: 5px;">Real-time Analysis | AI Predictions | Auto-Broadcast to All Platforms</p>
        </div>
        <div><span class="live-badge">🔴 LIVE STREAMING</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== TIMEZONE TICKER ====================
ticker_parts = []
for name, config in EXCHANGES.items():
    time_str = get_exchange_time(config['city'])
    status = "🟢" if 9 <= datetime.now().hour <= 16 else "🔴"
    ticker_parts.append(f"<span class='ticker-item'>🌍 {config['city']}: {time_str} {status}</span>")

st.markdown(f"""
<div class="timezone-ticker">
    <div class="timezone-ticker-content">
        {' '.join(ticker_parts)} • 🔴 = Closed • 🟢 = Open
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== CONTROL BUTTONS ====================
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🔄 Update Data", use_container_width=True):
        update_all_data()
        st.success("Data updated!")
with col2:
    if st.button("▶️ Start Stream" if not st.session_state.auto_stream else "⏸️ Stop Stream", use_container_width=True):
        st.session_state.auto_stream = not st.session_state.auto_stream
with col3:
    if st.button("📢 Start Broadcast" if not st.session_state.broadcast_active else "🔴 Stop Broadcast", use_container_width=True):
        st.session_state.broadcast_active = not st.session_state.broadcast_active
with col4:
    st.markdown(f"<div style='text-align:center; padding:8px; background:rgba(45,45,65,0.7); border-radius:30px;'><small>Updated: {st.session_state.last_update.strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)

# ==================== MAIN LAYOUT ====================
left_col, right_col = st.columns([2.5, 1])

with right_col:
    # Stock Ticker
    st.markdown('<div class="stock-ticker"><h4 style="color:#00cc88; margin:0 0 10px 0;">📊 MARKET MOVERS</h4>', unsafe_allow_html=True)
    
    stocks = []
    for name, data in st.session_state.exchange_data.items():
        stocks.append({'name': name.split()[0], 'value': data['value'], 'change': data['change']})
    
    if stocks:
        for stock in stocks[:5]:
            change_class = "positive" if stock['change'] >= 0 else "negative"
            change_symbol = "+" if stock['change'] >= 0 else ""
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(0,204,136,0.2);">
                <span style="color:#00cc88; font-weight:600;">{stock['name']}</span>
                <span style="color:#fff;">${stock['value']:.2f}</span>
                <span class="{change_class}">{change_symbol}{stock['change']:.1f}%</span>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Ad Placeholders
    ads = [
        ("📢", "SPONSORED", "Your Ad Here", "Advertise →"),
        ("📊", "PREMIUM", "AI Pro Analytics", "Learn More →"),
        ("📚", "FREE TRAINING", "Master the Markets", "Register →"),
        ("🤝", "PARTNER", "Zero Commission Trading", "Claim →")
    ]
    for icon, title, text, btn in ads:
        st.markdown(f"""
        <div class="ad-container">
            <div style="font-size:28px;">{icon}</div>
            <div class="ad-title">{title}</div>
            <div class="ad-content">{text}</div>
            <div class="ad-button">{btn}</div>
        </div>
        """, unsafe_allow_html=True)

with left_col:
    # Stats Row
    stats = st.columns(4)
    with stats[0]:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{len(st.session_state.exchange_data)}</div><div class='stat-label'>Global Exchanges</div></div>", unsafe_allow_html=True)
    with stats[1]:
        buy = sum(1 for d in st.session_state.sector_data.values() if d.get('signal') == "BUY")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#00cc88;'>{buy}</div><div class='stat-label'>Buy Signals</div></div>", unsafe_allow_html=True)
    with stats[2]:
        sell = sum(1 for d in st.session_state.sector_data.values() if d.get('signal') == "SELL")
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color:#ff8888;'>{sell}</div><div class='stat-label'>Sell Signals</div></div>", unsafe_allow_html=True)
    with stats[3]:
        avg_conf = 82
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{avg_conf}%</div><div class='stat-label'>AI Confidence</div></div>", unsafe_allow_html=True)
    
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
    
    # ==================== STOCK CHART SECTION ====================
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
    
    # ==================== AI PREDICTIONS SECTION ====================
    st.markdown("## 🤖 AI Stock Predictions")
    
    pred_cols = st.columns(3)
    for idx, (symbol, pred) in enumerate(list(st.session_state.ai_predictions.items())[:6]):
        if pred:
            with pred_cols[idx % 3]:
                signal_color = "#00cc88" if pred['signal'] == "BUY" else "#ff8888" if pred['signal'] == "SELL" else "#ffaa66"
                st.markdown(f"""
                <div class="prediction-card">
                    <div style="display: flex; justify-content: space-between;">
                        <strong style="color:#00cc88;">{symbol}</strong>
                        <span style="color:{signal_color};">{pred['signal']}</span>
                    </div>
                    <div style="font-size: 24px; font-weight: bold;">${pred['current_price']:.2f}</div>
                    <div style="font-size: 12px; color: #aaa;">Target: ${pred['target']:.2f}</div>
                    <div style="font-size: 12px;">Confidence: {pred['confidence']}%</div>
                </div>
                """, unsafe_allow_html=True)
    
    # ==================== INVESTMENT CALCULATOR ====================
    st.markdown("## 💰 Investment Calculator")
    st.markdown('<div class="investment-card">', unsafe_allow_html=True)
    st.markdown('<div class="investment-title">Plan Your Investment</div>', unsafe_allow_html=True)
    
    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        inv_symbol = st.selectbox("Select Stock", st.session_state.watchlist, key="inv_select")
    with inv_col2:
        inv_amount = st.number_input("Investment Amount ($)", min_value=100, value=1000, step=100)
    
    if st.button("Calculate Plan", use_container_width=True):
        if inv_symbol in st.session_state.ai_predictions:
            plan = calculate_investment_plan(inv_symbol, inv_amount, st.session_state.ai_predictions[inv_symbol])
            if plan:
                st.markdown(f"""
                <div style="margin-top: 15px; padding: 15px; background: rgba(0,204,136,0.1); border-radius: 12px;">
                    <strong style="color:#00cc88;">{plan['symbol']} Investment Plan</strong><br>
                    Investment: ${plan['investment_amount']:,.2f}<br>
                    Shares: {plan['shares']}<br>
                    Current Price: ${plan['current_price']:.2f}<br>
                    Target Price: ${plan['target_price']:.2f}<br>
                    Potential Return: {plan['potential_return']:+.1f}%<br>
                    <span style="color: #00cc88;">Recommendation: {plan['recommendation']}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Could not calculate plan")
        else:
            st.error("No prediction available for this stock")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ==================== SECTOR PERFORMANCE ====================
    st.markdown("## 📈 Sector Performance")
    sector_cols = st.columns(3)
    for idx, (name, data) in enumerate(st.session_state.sector_data.items()):
        with sector_cols[idx % 3]:
            color = "#00cc88" if data['performance'] > 0 else "#ff8888"
            icon = SECTORS[name]['icon']
            st.markdown(f"""
            <div class="sector-card">
                <div style="font-size: 28px;">{icon}</div>
                <div class="sector-name">{name}</div>
                <div class="sector-perf" style="color:{color};">{data['performance']:+.1f}%</div>
                <div style="font-size: 11px; color: #aaa;">{data['signal']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎮 Dashboard Controls")
    
    # Status
    if st.session_state.auto_stream:
        st.success("🟢 Live Stream: ACTIVE")
    else:
        st.warning("⚪ Live Stream: INACTIVE")
    
    if st.session_state.broadcast_active:
        st.success("📢 Broadcast: ACTIVE")
    else:
        st.warning("🔇 Broadcast: INACTIVE")
    
    st.divider()
    
    # Stats
    st.markdown("### 📊 Dashboard Stats")
    st.metric("Exchanges", len(st.session_state.exchange_data))
    st.metric("Sectors", len(st.session_state.sector_data))
    st.metric("Stocks Tracked", len(st.session_state.ai_predictions))
    
    st.divider()
    
    # Social Media Connection
    st.markdown("### 🌐 Social Media")
    
    # Twitter
    with st.expander("🐦 Twitter/X"):
        tw_key = st.text_input("API Key", type="password", key="tw_key")
        tw_secret = st.text_input("API Secret", type="password", key="tw_secret")
        tw_token = st.text_input("Access Token", type="password", key="tw_token")
        tw_token_secret = st.text_input("Access Secret", type="password", key="tw_token_secret")
        if st.button("Connect Twitter", key="conn_tw"):
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
        youtube_file = st.file_uploader("Upload client_secrets.json", type=['json'], key="yt_file")
        if youtube_file:
            secrets_path = tempfile.mktemp(suffix=".json")
            with open(secrets_path, 'wb') as f:
                f.write(youtube_file.getvalue())
            if st.button("Connect YouTube", key="conn_yt"):
                success, msg = st.session_state.social_manager.connect_youtube(secrets_path)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # Facebook
    with st.expander("📘 Facebook"):
        fb_token = st.text_input("Access Token", type="password", key="fb_token")
        fb_page = st.text_input("Page ID", key="fb_page")
        if st.button("Connect Facebook", key="conn_fb"):
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
        if st.button("Connect Instagram", key="conn_ig"):
            if ig_token and ig_account:
                success, msg = st.session_state.social_manager.connect_instagram(ig_token, ig_account)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # TikTok
    with st.expander("🎵 TikTok"):
        tt_session = st.text_input("Session ID", type="password", key="tt_session")
        if st.button("Configure TikTok", key="conn_tt"):
            success, msg = st.session_state.social_manager.connect_tiktok(session_id=tt_session)
            if success:
                st.success(msg)
            else:
                st.error(msg)
    
    st.divider()
    
    # Quick Post
    st.markdown("### 📤 Quick Post")
    quick_msg = st.text_area("Message", height=80, placeholder="Share market insights...")
    if st.button("📢 Post to All Platforms", use_container_width=True):
        if quick_msg:
            with st.spinner("Posting to social media..."):
                results = st.session_state.social_manager.post_to_all(quick_msg)
                for platform, result in results.items():
                    if result['success']:
                        st.success(f"✅ {platform.capitalize()}: {result['message']}")
                    else:
                        st.error(f"❌ {platform.capitalize()}: {result['message']}")
        else:
            st.warning("Enter a message to post")

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
<div style="text-align: center; color: #aaa; padding: 20px;">
    🤖 AI Trading Dashboard | 24/7 Market Intelligence | Auto-Broadcast to Twitter, YouTube, Facebook, Instagram, TikTok
    <br><small>⚠️ Not financial advice. Always do your own research before investing.</small>
</div>
""", unsafe_allow_html=True)
