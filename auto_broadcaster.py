import time
import threading
import schedule
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import requests
import json
import os
import tempfile
from gtts import gTTS
import warnings

warnings.filterwarnings('ignore')

# Try to import moviepy with fallback
try:
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("Warning: moviepy not available. Video features disabled.")

# Try to import matplotlib for charts
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class AutoBroadcaster:
    """Autonomous content creation and broadcasting system"""
    
    def __init__(self, social_streamer=None):
        self.social_streamer = social_streamer
        self.content_queue = []
        self.broadcast_schedule = {}
        self.is_running = False
        self.broadcast_log = []
        
    def start_broadcasting(self):
        """Start autonomous broadcasting"""
        self.is_running = True
        
        # Schedule different content types
        schedule.every(1).minutes.do(self.broadcast_market_update)
        schedule.every(5).minutes.do(self.broadcast_top_movers)
        schedule.every(15).minutes.do(self.broadcast_sector_analysis)
        schedule.every(30).minutes.do(self.broadcast_trading_alerts)
        schedule.every(1).hours.do(self.broadcast_daily_summary)
        
        # Start background thread
        thread = threading.Thread(target=self._run_scheduler, daemon=True)
        thread.start()
        
        self._log_broadcast("Auto-broadcaster started")
        return "Broadcasting started"
    
    def stop_broadcasting(self):
        """Stop autonomous broadcasting"""
        self.is_running = False
        self._log_broadcast("Auto-broadcaster stopped")
        return "Broadcasting stopped"
    
    def _run_scheduler(self):
        """Run the scheduler in background"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def _log_broadcast(self, message):
        """Log broadcast activity"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.broadcast_log.append(f"[{timestamp}] {message}")
        # Keep only last 100 logs
        self.broadcast_log = self.broadcast_log[-100:]
    
    def broadcast_market_update(self):
        """Create and broadcast market update"""
        try:
            # Get market data
            spy = yf.Ticker("SPY")
            info = spy.info
            price = info.get('regularMarketPrice', 0)
            change = info.get('regularMarketChangePercent', 0)
            
            if price == 0:
                return
            
            # Create message
            sentiment = "🟢 BULLISH" if change > 0 else "🔴 BEARISH"
            message = f"""📊 MARKET UPDATE - {datetime.now().strftime('%H:%M')}
            
S&P 500: ${price:.2f} ({change:+.2f}%)
Market Sentiment: {sentiment}
AI Confidence: {min(95, abs(change)*20 + 60):.0f}%

#MarketUpdate #Stocks #Trading #SP500"""
            
            # Create chart if available
            chart_path = self.create_market_chart('SPY')
            
            # Broadcast to all platforms
            if self.social_streamer:
                self.social_streamer.stream_to_all(
                    data={'symbol': 'SPY'},
                    message=message,
                    image_path=chart_path
                )
            
            self._log_broadcast(f"Market update broadcast: SPY ${price:.2f} ({change:+.1f}%)")
            
            # Clean up temp file
            if chart_path and os.path.exists(chart_path):
                try:
                    os.remove(chart_path)
                except:
                    pass
            
        except Exception as e:
            self._log_broadcast(f"Market update error: {str(e)}")
    
    def broadcast_top_movers(self):
        """Broadcast top gainers and losers"""
        try:
            # Get top gainers from major indices
            indices = ['SPY', 'QQQ', 'IWM']
            top_movers = []
            
            for symbol in indices:
                stock = yf.Ticker(symbol)
                info = stock.info
                price = info.get('regularMarketPrice', 0)
                change = info.get('regularMarketChangePercent', 0)
                if price > 0:
                    top_movers.append(f"{symbol}: {change:+.1f}%")
            
            if not top_movers:
                return
            
            message = f"""🚀 TOP MOVERS {datetime.now().strftime('%H:%M')}
            
{' | '.join(top_movers)}

Biggest gainers today: Check your watchlist!

#TopMovers #StockMarket #Gainers #Losers"""
            
            if self.social_streamer:
                self.social_streamer.stream_to_all(
                    data={'symbol': 'MARKET'},
                    message=message
                )
            
            self._log_broadcast(f"Top movers broadcast: {', '.join(top_movers)}")
            
        except Exception as e:
            self._log_broadcast(f"Top movers error: {str(e)}")
    
    def broadcast_sector_analysis(self):
        """Broadcast sector performance analysis"""
        try:
            sectors = {
                'XLK': 'Tech', 'XLF': 'Financials', 'XLV': 'Healthcare',
                'XLE': 'Energy', 'XLI': 'Industrials', 'XLU': 'Utilities'
            }
            
            sector_performance = []
            strongest = None
            strongest_change = -100
            weakest = None
            weakest_change = 100
            
            for etf, name in sectors.items():
                try:
                    ticker = yf.Ticker(etf)
                    info = ticker.info
                    change = info.get('regularMarketChangePercent', 0)
                    
                    if change > strongest_change:
                        strongest_change = change
                        strongest = name
                    if change < weakest_change:
                        weakest_change = change
                        weakest = name
                    
                    emoji = "🟢" if change > 0 else "🔴"
                    sector_performance.append(f"{emoji} {name}: {change:+.1f}%")
                except:
                    pass
            
            if not sector_performance:
                return
            
            message = f"""📈 SECTOR ANALYSIS {datetime.now().strftime('%H:%M')}
            
{' | '.join(sector_performance[:6])}

Strongest: {strongest} ({strongest_change:+.1f}%)
Weakest: {weakest} ({weakest_change:+.1f}%)

#SectorAnalysis #MarketTrends #TradingStrategy"""
            
            if self.social_streamer:
                self.social_streamer.stream_to_all(
                    data={'symbol': 'SECTORS'},
                    message=message
                )
            
            self._log_broadcast(f"Sector analysis broadcast: {strongest} strongest, {weakest} weakest")
            
        except Exception as e:
            self._log_broadcast(f"Sector analysis error: {str(e)}")
    
    def broadcast_trading_alerts(self):
        """Broadcast active trading alerts"""
        try:
            # Get top alerts from main app if available
            alerts = self.get_active_alerts()
            
            if alerts:
                message = f"""🚨 TRADING ALERTS {datetime.now().strftime('%H:%M')}
                
"""
                for alert in alerts[:3]:
                    emoji = "🟢" if "BUY" in alert['type'] else "🔴"
                    message += f"{emoji} {alert['symbol']}: {alert['type']} @ ${alert['price']:.2f}\n   Confidence: {alert['confidence']}%\n\n"
                
                message += "#TradingAlerts #StockSignals #AITrading"
                
                if self.social_streamer:
                    self.social_streamer.stream_to_all(
                        data={'symbol': 'ALERTS'},
                        message=message
                    )
                
                self._log_broadcast(f"Trading alerts broadcast: {len(alerts)} alerts")
            
        except Exception as e:
            self._log_broadcast(f"Trading alerts error: {str(e)}")
    
    def broadcast_daily_summary(self):
        """Broadcast daily market summary"""
        try:
            # Get daily performance
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1d")
            
            if not hist.empty and len(hist) > 0:
                open_price = hist['Open'].iloc[0]
                close_price = hist['Close'].iloc[-1]
                day_change = ((close_price - open_price) / open_price * 100) if open_price else 0
                
                message = f"""📊 DAILY MARKET SUMMARY - {datetime.now().strftime('%Y-%m-%d')}
                
S&P 500: ${close_price:.2f} ({day_change:+.2f}%)
Day Range: ${hist['Low'].min():.2f} - ${hist['High'].max():.2f}
Volume: {int(hist['Volume'].sum()):,}

Top Performers: Tech & Financials
AI Prediction: {'Bullish' if day_change > 0 else 'Bearish'}

#DailySummary #MarketWrap #TradingRecap"""
                
                # Try to create video summary if moviepy available
                video_path = None
                if MOVIEPY_AVAILABLE:
                    video_path = self.create_summary_video(day_change)
                
                if self.social_streamer:
                    self.social_streamer.stream_to_all(
                        data={'symbol': 'DAILY'},
                        message=message,
                        video_path=video_path
                    )
                
                # Clean up video
                if video_path and os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except:
                        pass
                
                self._log_broadcast(f"Daily summary broadcast: {day_change:+.1f}%")
            
        except Exception as e:
            self._log_broadcast(f"Daily summary error: {str(e)}")
    
    def create_market_chart(self, symbol):
        """Create chart image for broadcasting"""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d", interval="5m")
            
            if not hist.empty and len(hist) > 1:
                plt.style.use('dark_background')
                fig, ax = plt.subplots(figsize=(10, 6))
                
                ax.plot(hist.index, hist['Close'], color='#00ff88', linewidth=2)
                ax.fill_between(hist.index, hist['Close'].min(), hist['Close'], alpha=0.3, color='#00ff88')
                ax.set_title(f"{symbol} - {datetime.now().strftime('%Y-%m-%d %H:%M')}", color='white', fontsize=14)
                ax.set_ylabel('Price ($)', color='white')
                ax.grid(alpha=0.3)
                ax.set_facecolor('#111111')
                
                chart_path = tempfile.mktemp(suffix=".png")
                plt.savefig(chart_path, bbox_inches='tight', facecolor='#111111')
                plt.close()
                
                return chart_path
            else:
                return None
            
        except Exception as e:
            self._log_broadcast(f"Chart creation error: {str(e)}")
            return None
    
    def create_summary_video(self, day_change):
        """Create video summary for daily broadcast"""
        if not MOVIEPY_AVAILABLE:
            return None
        
        try:
            # Create text
            text = f"Market Summary\n{datetime.now().strftime('%Y-%m-%d')}\n\nS&P 500: {day_change:+.2f}%\n\nAI Analysis: {'Bullish' if day_change > 0 else 'Bearish'}"
            
            # Create audio
            tts = gTTS(text)
            audio_path = tempfile.mktemp(suffix=".mp3")
            tts.save(audio_path)
            
            # Create video clip
            txt_clip = TextClip(text, fontsize=40, color='white', font='Arial', size=(1080, 1920))
            txt_clip = txt_clip.set_duration(15).set_position('center')
            
            video_path = tempfile.mktemp(suffix=".mp4")
            txt_clip.write_videofile(video_path, fps=24, verbose=False, logger=None)
            
            # Clean up audio
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return video_path
            
        except Exception as e:
            self._log_broadcast(f"Video creation error: {str(e)}")
            return None
    
    def get_active_alerts(self):
        """Get active trading alerts"""
        # Try to get from main app's session state
        try:
            import streamlit as st
            if hasattr(st.session_state, 'global_alerts') and st.session_state.global_alerts:
                alerts = []
                for alert in st.session_state.global_alerts[-5:]:
                    alerts.append({
                        'symbol': alert.symbol,
                        'type': alert.alert_type,
                        'price': alert.price,
                        'confidence': alert.confidence
                    })
                return alerts
        except:
            pass
        
        # Fallback: analyze some stocks
        try:
            symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT']
            alerts = []
            
            for symbol in symbols:
                stock = yf.Ticker(symbol)
                info = stock.info
                price = info.get('regularMarketPrice', 0)
                change = info.get('regularMarketChangePercent', 0)
                
                if price > 0:
                    if change > 2:
                        alert_type = "BUY"
                        confidence = 75
                    elif change < -2:
                        alert_type = "SELL"
                        confidence = 75
                    else:
                        continue
                    
                    alerts.append({
                        'symbol': symbol,
                        'type': alert_type,
                        'price': price,
                        'confidence': confidence
                    })
            
            return alerts[:3]
            
        except:
            return []
    
    def get_broadcast_log(self):
        """Get broadcast log"""
        return self.broadcast_log
    
    def get_status(self):
        """Get broadcaster status"""
        return {
            'is_running': self.is_running,
            'total_broadcasts': len(self.broadcast_log),
            'last_broadcast': self.broadcast_log[-1] if self.broadcast_log else None,
            'moviepy_available': MOVIEPY_AVAILABLE,
            'matplotlib_available': MATPLOTLIB_AVAILABLE
        }

# Simple test function
if __name__ == "__main__":
    broadcaster = AutoBroadcaster()
    print("AutoBroadcaster initialized")
    print(f"MoviePy available: {MOVIEPY_AVAILABLE}")
    print(f"Matplotlib available: {MATPLOTLIB_AVAILABLE}")
