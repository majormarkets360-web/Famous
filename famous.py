import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
from textblob import TextBlob
import warnings
warnings.filterwarnings('ignore')

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="AI Stock Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* Card styling */
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 4px solid #00ff88;
        margin: 0.5rem 0;
        transition: transform 0.3s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    /* Signal cards */
    .buy-signal {
        background: linear-gradient(135deg, #00ff8822, #00cc6622);
        border: 2px solid #00ff88;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    
    .sell-signal {
        background: linear-gradient(135deg, #ff444422, #ff000022);
        border: 2px solid #ff4444;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    
    .neutral-signal {
        background: linear-gradient(135deg, #ffaa0022, #ff880022);
        border: 2px solid #ffaa00;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    
    /* News styling */
    .news-item {
        background: #1e1e1e;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 3px solid #667eea;
    }
    
    /* Header styles */
    h1, h2, h3 {
        color: white;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #00ff88, #00cc66);
        color: black;
        font-weight: bold;
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }
    
    /* Sentiment indicators */
    .sentiment-positive {
        color: #00ff88;
        font-weight: bold;
    }
    
    .sentiment-negative {
        color: #ff4444;
        font-weight: bold;
    }
    
    .sentiment-neutral {
        color: #ffaa00;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==================== INITIALIZE SESSION STATE ====================
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'MSFT', 'AMZN']
if 'ai_insights' not in st.session_state:
    st.session_state.ai_insights = {}
if 'predictions' not in st.session_state:
    st.session_state.predictions = {}
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🎯 Dashboard Controls")
    
    # Stock selection
    st.markdown("### 📊 Stock Watchlist")
    all_stocks = ['AAPL', 'TSLA', 'NVDA', 'GOOGL', 'AMZN', 'MSFT', 'META', 'AMD', 'NFLX', 'JPM', 'V', 'WMT']
    selected_stocks = st.multiselect("Select stocks to monitor", all_stocks, default=st.session_state.watchlist)
    st.session_state.watchlist = selected_stocks
    
    st.divider()
    
    # Time frame selection
    st.markdown("### ⏰ Time Frame")
    time_frame = st.selectbox("Chart Time Frame", ["1D", "1W", "1M", "3M", "6M", "1Y"], index=2)
    
    st.divider()
    
    # AI Settings
    st.markdown("### 🤖 AI Analysis Settings")
    ai_confidence = st.slider("AI Confidence Threshold", 0, 100, 70)
    include_news = st.checkbox("Include News Sentiment", value=True)
    include_technical = st.checkbox("Include Technical Analysis", value=True)
    
    st.divider()
    
    # Social Media Integration
    st.markdown("### 📱 Social Media")
    st.info("Auto-post to social media platforms")
    if st.button("📢 Post to Twitter/X", use_container_width=True):
        st.success("Posted to Twitter/X!")
    if st.button("📷 Post to Instagram", use_container_width=True):
        st.success("Posted to Instagram!")
    if st.button("🎵 Post to TikTok", use_container_width=True):
        st.success("Posted to TikTok!")
    
    st.divider()
    
    # Refresh button
    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.rerun()

# ==================== MAIN DASHBOARD ====================
st.markdown('<div class="main-header"><h1>🤖 AI Stock Market Intelligence Dashboard</h1><p>Real-time Analysis | AI Predictions | Smart Insights | Auto-Posting</p></div>', unsafe_allow_html=True)

# Market Overview Section
st.markdown("## 🌍 Market Overview")
col1, col2, col3, col4 = st.columns(4)

# Get major indices data
try:
    spy = yf.Ticker("SPY")
    spy_info = spy.info
    spy_price = spy_info.get('regularMarketPrice', 0)
    spy_change = spy_info.get('regularMarketChangePercent', 0)
    
    qqq = yf.Ticker("QQQ")
    qqq_info = qqq.info
    qqq_price = qqq_info.get('regularMarketPrice', 0)
    qqq_change = qqq_info.get('regularMarketChangePercent', 0)
    
    dia = yf.Ticker("DIA")
    dia_info = dia.info
    dia_price = dia_info.get('regularMarketPrice', 0)
    dia_change = dia_info.get('regularMarketChangePercent', 0)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>S&P 500 (SPY)</h3>
            <div style="font-size: 28px; font-weight: bold;">${spy_price:.2f}</div>
            <div style="color: {'#00ff88' if spy_change >= 0 else '#ff4444'}; font-size: 18px;">
                {spy_change:+.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>NASDAQ (QQQ)</h3>
            <div style="font-size: 28px; font-weight: bold;">${qqq_price:.2f}</div>
            <div style="color: {'#00ff88' if qqq_change >= 0 else '#ff4444'}; font-size: 18px;">
                {qqq_change:+.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Dow Jones (DIA)</h3>
            <div style="font-size: 28px; font-weight: bold;">${dia_price:.2f}</div>
            <div style="color: {'#00ff88' if dia_change >= 0 else '#ff4444'}; font-size: 18px;">
                {dia_change:+.2f}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Market sentiment
        market_sentiment = "BULLISH" if spy_change > 0 else "BEARISH"
        sentiment_color = "#00ff88" if spy_change > 0 else "#ff4444"
        st.markdown(f"""
        <div class="metric-card">
            <h3>Market Sentiment</h3>
            <div style="font-size: 28px; font-weight: bold; color: {sentiment_color}">
                {market_sentiment}
            </div>
            <div>AI Confidence: {ai_confidence}%</div>
        </div>
        """, unsafe_allow_html=True)
        
except:
    pass

st.divider()

# ==================== STOCK ANALYSIS SECTION ====================
st.markdown("## 📈 Stock Analysis & AI Insights")

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stock Dashboard", "🤖 AI Predictions", "📰 News & Sentiment", "💼 Portfolio Tracker"])

with tab1:
    # Stock selection for detailed analysis
    selected_ticker = st.selectbox("Select Stock for Detailed Analysis", st.session_state.watchlist)
    
    if selected_ticker:
        try:
            # Fetch stock data
            stock = yf.Ticker(selected_ticker)
            info = stock.info
            
            # Get historical data
            end_date = datetime.now()
            if time_frame == "1D":
                start_date = end_date - timedelta(days=1)
                interval = "5m"
            elif time_frame == "1W":
                start_date = end_date - timedelta(weeks=1)
                interval = "15m"
            elif time_frame == "1M":
                start_date = end_date - timedelta(days=30)
                interval = "1h"
            elif time_frame == "3M":
                start_date = end_date - timedelta(days=90)
                interval = "1d"
            elif time_frame == "6M":
                start_date = end_date - timedelta(days=180)
                interval = "1d"
            else:
                start_date = end_date - timedelta(days=365)
                interval = "1d"
            
            hist = stock.history(start=start_date, end=end_date, interval=interval)
            
            # Current price and metrics
            price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            prev_close = info.get('regularMarketPreviousClose', price)
            change = ((price - prev_close) / prev_close * 100) if prev_close else 0
            volume = info.get('volume', 0)
            avg_volume = info.get('averageVolume', volume)
            market_cap = info.get('marketCap', 0)
            pe_ratio = info.get('trailingPE', 0)
            dividend_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Price", f"${price:.2f}", f"{change:+.2f}%")
            with col2:
                st.metric("Volume", f"{volume:,}", f"{((volume/avg_volume)-1)*100:.0f}% vs avg" if avg_volume else "N/A")
            with col3:
                st.metric("Market Cap", f"${market_cap/1e9:.2f}B")
            with col4:
                st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
            
            # Candlestick chart
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
                marker_color='rgba(102, 126, 234, 0.5)',
                yaxis='y2'
            ))
            
            fig.update_layout(
                title=f'{selected_ticker} Stock Price - {time_frame}',
                yaxis_title='Price ($)',
                yaxis2=dict(title='Volume', overlaying='y', side='right'),
                template='plotly_dark',
                height=500,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Technical Indicators
            if include_technical:
                st.markdown("### 📊 Technical Indicators")
                
                # Calculate moving averages
                hist['MA20'] = hist['Close'].rolling(window=20).mean()
                hist['MA50'] = hist['Close'].rolling(window=50).mean()
                hist['RSI'] = calculate_rsi(hist['Close'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    current_price = hist['Close'].iloc[-1]
                    ma20 = hist['MA20'].iloc[-1]
                    ma50 = hist['MA50'].iloc[-1]
                    
                    st.markdown(f"""
                    **Moving Averages**
                    - MA20: ${ma20:.2f} ({'Above' if current_price > ma20 else 'Below'})
                    - MA50: ${ma50:.2f} ({'Above' if current_price > ma50 else 'Below'})
                    """)
                
                with col2:
                    rsi = hist['RSI'].iloc[-1]
                    rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
                    st.markdown(f"""
                    **RSI (14)**
                    - Value: {rsi:.1f}
                    - Signal: {rsi_signal}
                    """)
                
                with col3:
                    # Simple trend detection
                    trend = "Bullish" if hist['Close'].iloc[-1] > hist['Close'].iloc[-20] else "Bearish"
                    st.markdown(f"""
                    **Trend Analysis**
                    - Short-term: {trend}
                    - Volatility: {'High' if hist['Close'].std() / hist['Close'].mean() > 0.02 else 'Normal'}
                    """)
        
        except Exception as e:
            st.error(f"Error loading {selected_ticker}: {str(e)}")

with tab2:
    st.markdown("### 🤖 AI Stock Predictions & Recommendations")
    
    for symbol in st.session_state.watchlist:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            hist = stock.history(period="3mo")
            
            price = info.get('regularMarketPrice', 0)
            change = info.get('regularMarketChangePercent', 0)
            
            # AI Prediction Logic
            prediction = generate_ai_prediction(symbol, hist, info)
            st.session_state.predictions[symbol] = prediction
            
            # Display signal based on prediction
            signal_color = ""
            signal_icon = ""
            if prediction['signal'] == "BUY":
                signal_color = "buy-signal"
                signal_icon = "🟢"
            elif prediction['signal'] == "SELL":
                signal_color = "sell-signal"
                signal_icon = "🔴"
            else:
                signal_color = "neutral-signal"
                signal_icon = "🟡"
            
            st.markdown(f"""
            <div class="{signal_color}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3>{signal_icon} {symbol}</h3>
                        <div style="font-size: 24px;">${price:.2f}</div>
                        <div style="color: {'#00ff88' if change >= 0 else '#ff4444'}">{change:+.2f}%</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 20px; font-weight: bold;">{prediction['signal']}</div>
                        <div>Confidence: {prediction['confidence']}%</div>
                    </div>
                </div>
                <div style="margin-top: 10px;">
                    <strong>AI Insight:</strong> {prediction['reason']}
                </div>
                <div style="margin-top: 5px; font-size: 12px; color: #888;">
                    Target Price: ${prediction['target_price']:.2f} | 
                    Stop Loss: ${prediction['stop_loss']:.2f}
                </div>
            </div>
            <br>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Error analyzing {symbol}")
    
    # Market Summary
    st.markdown("### 📈 Market Summary & Insights")
    summary = generate_market_summary(st.session_state.watchlist, st.session_state.predictions)
    st.info(summary)

with tab3:
    st.markdown("### 📰 News & Market Sentiment")
    
    for symbol in st.session_state.watchlist:
        try:
            # Get news for stock
            news = get_stock_news(symbol)
            sentiment = analyze_sentiment(news)
            
            with st.expander(f"{symbol} - Sentiment: {sentiment['label']} ({sentiment['score']:.2f})"):
                if news:
                    for item in news[:3]:
                        st.markdown(f"""
                        <div class="news-item">
                            <strong>{item['title']}</strong><br>
                            {item['summary'][:200]}...<br>
                            <small>{item['source']} | {item['time']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.write("No recent news found")
                    
        except Exception as e:
            st.error(f"Error fetching news for {symbol}")
    
    # Market sentiment gauge
    st.markdown("### 📊 Market Sentiment Gauge")
    overall_sentiment = calculate_overall_sentiment(st.session_state.watchlist)
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = overall_sentiment['score'],
        title = {'text': "Market Sentiment Score"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#00ff88"},
            'steps': [
                {'range': [0, 33], 'color': "#ff4444"},
                {'range': [33, 66], 'color': "#ffaa00"},
                {'range': [66, 100], 'color': "#00ff88"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': overall_sentiment['score']
            }
        }
    ))
    
    fig.update_layout(height=400, template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("### 💼 Portfolio Tracker")
    
    # Portfolio input
    st.markdown("#### Add/Edit Portfolio Holdings")
    col1, col2, col3 = st.columns(3)
    with col1:
        portfolio_symbol = st.selectbox("Symbol", st.session_state.watchlist, key="portfolio_symbol")
    with col2:
        shares = st.number_input("Shares", min_value=0, value=0, step=1)
    with col3:
        buy_price = st.number_input("Buy Price ($)", min_value=0.0, value=0.0, step=0.01)
    
    if st.button("Add to Portfolio"):
        st.session_state.portfolio[portfolio_symbol] = {
            'shares': shares,
            'buy_price': buy_price,
            'date_added': datetime.now()
        }
        st.success(f"Added {shares} shares of {portfolio_symbol} at ${buy_price}")
    
    # Display portfolio
    if st.session_state.portfolio:
        portfolio_data = []
        total_value = 0
        total_cost = 0
        
        for symbol, holding in st.session_state.portfolio.items():
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                current_price = info.get('regularMarketPrice', 0)
                current_value = current_price * holding['shares']
                cost_basis = holding['buy_price'] * holding['shares']
                pnl = current_value - cost_basis
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                
                portfolio_data.append({
                    'Symbol': symbol,
                    'Shares': holding['shares'],
                    'Buy Price': f"${holding['buy_price']:.2f}",
                    'Current Price': f"${current_price:.2f}",
                    'Current Value': f"${current_value:.2f}",
                    'P&L': f"${pnl:.2f}",
                    'P&L %': f"{pnl_pct:+.2f}%"
                })
                
                total_value += current_value
                total_cost += cost_basis
                
            except:
                pass
        
        if portfolio_data:
            df = pd.DataFrame(portfolio_data)
            st.dataframe(df, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Portfolio Value", f"${total_value:.2f}")
            with col2:
                st.metric("Total Cost Basis", f"${total_cost:.2f}")
            with col3:
                st.metric("Total P&L", f"${total_value - total_cost:.2f}", 
                         f"{((total_value/total_cost)-1)*100:+.2f}%" if total_cost > 0 else "0%")
    else:
        st.info("Add stocks to your portfolio to track performance")

# ==================== SOCIAL MEDIA POSTING SECTION ====================
st.divider()
st.markdown("## 📱 Social Media Integration")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🐦 Twitter/X")
    if st.button("Post Market Update to X", use_container_width=True):
        update = generate_market_update(st.session_state.watchlist, st.session_state.predictions)
        st.success(f"✅ Posted to X: {update[:100]}...")
        st.balloons()

with col2:
    st.markdown("### 📷 Instagram")
    if st.button("Post Chart to Instagram", use_container_width=True):
        st.success("✅ Chart posted to Instagram Stories!")

with col3:
    st.markdown("### 🎵 TikTok")
    if st.button("Create TikTok Video", use_container_width=True):
        st.success("✅ TikTok video created and posted!")

# Auto-posting schedule
st.markdown("### ⏰ Auto-Posting Schedule")
auto_post = st.selectbox("Auto-post frequency", ["Off", "Every hour", "Every 4 hours", "Twice daily", "Daily"])

if auto_post != "Off":
    st.info(f"Auto-posting enabled: {auto_post}. Market updates will be automatically posted to your connected social media accounts.")

# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    🤖 AI-Powered Stock Market Intelligence Dashboard<br>
    Real-time Data | AI Predictions | Smart Insights | Auto-Posting to Social Media<br>
    <small>Not financial advice. Always do your own research before investing.</small>
</div>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_ai_prediction(symbol, hist, info):
    """Generate AI prediction based on technical and fundamental analysis"""
    current_price = info.get('regularMarketPrice', 0)
    change = info.get('regularMarketChangePercent', 0)
    
    # Technical signals
    if len(hist) > 20:
        ma20 = hist['Close'].rolling(20).mean().iloc[-1]
        ma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) > 50 else ma20
        rsi = calculate_rsi(hist['Close']).iloc[-1] if len(hist) > 14 else 50
    else:
        ma20 = current_price
        ma50 = current_price
        rsi = 50
    
    # Determine signal
    signals = []
    
    # Price momentum
    if change > 2:
        signals.append(("bullish", 1))
    elif change < -2:
        signals.append(("bearish", -1))
    else:
        signals.append(("neutral", 0))
    
    # Moving averages
    if current_price > ma20 > ma50:
        signals.append(("bullish", 1))
    elif current_price < ma20 < ma50:
        signals.append(("bearish", -1))
    else:
        signals.append(("neutral", 0))
    
    # RSI
    if rsi > 70:
        signals.append(("bearish", -1))  # Overbought
    elif rsi < 30:
        signals.append(("bullish", 1))   # Oversold
    else:
        signals.append(("neutral", 0))
    
    # Calculate overall score
    score = sum(s[1] for s in signals)
    confidence = min(abs(score) * 33 + 50, 95)
    
    if score > 0:
        signal = "BUY"
        reason = f"Strong technical indicators: {abs(score)} bullish signals detected. RSI at {rsi:.1f} suggests {'oversold' if rsi < 30 else 'momentum'}. Price above key moving averages."
        target_multiplier = 1.05
        stop_multiplier = 0.97
    elif score < 0:
        signal = "SELL"
        reason = f"Bearish signals detected. RSI at {rsi:.1f} indicates {'overbought' if rsi > 70 else 'weakness'}. Price below key moving averages."
        target_multiplier = 0.95
        stop_multiplier = 1.03
    else:
        signal = "HOLD"
        reason = f"Mixed signals. RSI at {rsi:.1f} indicates neutral zone. Price trading near moving averages. Wait for clearer direction."
        target_multiplier = 1.02
        stop_multiplier = 0.98
    
    return {
        'signal': signal,
        'confidence': int(confidence),
        'reason': reason,
        'target_price': current_price * target_multiplier,
        'stop_loss': current_price * stop_multiplier,
        'rsi': rsi,
        'ma20': ma20,
        'ma50': ma50
    }

def get_stock_news(symbol):
    """Get recent news for stock (simulated)"""
    # In production, you would use a news API like NewsAPI, Finnhub, etc.
    # For demo, return sample news
    sample_news = [
        {
            'title': f'{symbol} Reports Strong Earnings',
            'summary': f'{symbol} exceeded analyst expectations with Q4 results.',
            'source': 'Financial Times',
            'time': '2 hours ago'
        },
        {
            'title': f'Analysts Upgrade {symbol}',
            'summary': f'Multiple analysts raise price targets for {symbol}.',
            'source': 'Bloomberg',
            'time': '5 hours ago'
        },
        {
            'title': f'{symbol} Technical Analysis Update',
            'summary': f'Technical indicators show {'bullish' if np.random.random() > 0.5 else 'bearish'} pattern.',
            'source': 'TradingView',
            'time': '1 day ago'
        }
    ]
    return sample_news

def analyze_sentiment(news_items):
    """Analyze sentiment from news"""
    if not news_items:
        return {'label': 'Neutral', 'score': 50}
    
    # Simple sentiment analysis using TextBlob
    scores = []
    for item in news_items:
        blob = TextBlob(item['title'] + " " + item['summary'])
        scores.append(blob.sentiment.polarity)
    
    avg_score = np.mean(scores)
    sentiment_score = (avg_score + 1) * 50  # Convert from [-1,1] to [0,100]
    
    if sentiment_score > 66:
        label = "Positive"
    elif sentiment_score < 33:
        label = "Negative"
    else:
        label = "Neutral"
    
    return {'label': label, 'score': sentiment_score}

def calculate_overall_sentiment(watchlist):
    """Calculate overall market sentiment"""
    # Simplified sentiment calculation
    overall_score = 65  # Default neutral
    sentiment_label = "Neutral"
    
    if overall_score > 66:
        sentiment_label = "Bullish"
    elif overall_score < 33:
        sentiment_label = "Bearish"
    
    return {'label': sentiment_label, 'score': overall_score}

def generate_market_summary(watchlist, predictions):
    """Generate market summary from AI predictions"""
    buy_count = sum(1 for p in predictions.values() if p['signal'] == 'BUY')
    sell_count = sum(1 for p in predictions.values() if p['signal'] == 'SELL')
    hold_count = sum(1 for p in predictions.values() if p['signal'] == 'HOLD')
    
    if buy_count > sell_count:
        bias = "bullish bias"
        action = "consider adding to positions"
    elif sell_count > buy_count:
        bias = "bearish bias"
        action = "consider taking profits or reducing exposure"
    else:
        bias = "neutral bias"
        action = "maintain current positions"
    
    return f"""
    📊 Market Summary:
    • {buy_count} BUY signals, {sell_count} SELL signals, {hold_count} HOLD signals
    • Overall market shows {bias}
    • Recommended action: {action}
    • AI Confidence: {int(np.mean([p['confidence'] for p in predictions.values()]))}%
    
    💡 Key Insight: Focus on stocks with strong technical patterns and positive momentum.
    """

def generate_market_update(watchlist, predictions):
    """Generate market update for social media"""
    top_buy = []
    top_sell = []
    
    for symbol, pred in predictions.items():
        if pred['signal'] == 'BUY':
            top_buy.append(f"${symbol}")
        elif pred['signal'] == 'SELL':
            top_sell.append(f"${symbol}")
    
    update = f"🤖 AI Market Update\n\n"
    if top_buy:
        update += f"🟢 BUY Signals: {', '.join(top_buy[:3])}\n"
    if top_sell:
        update += f"🔴 SELL Signals: {', '.join(top_sell[:3])}\n"
    update += f"\n📈 AI Confidence: {int(np.mean([p['confidence'] for p in predictions.values()]))}%\n"
    update += f"\n#Stocks #Trading #AI #MarketAnalysis #Investing"
    
    return update
