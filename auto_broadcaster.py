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
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
from gtts import gTTS
import tempfile

class AutoBroadcaster:
    """Autonomous content creation and broadcasting system"""
    
    def __init__(self, social_streamer):
        self.social_streamer = social_streamer
        self.content_queue = []
        self.broadcast_schedule = {}
        self.is_running = False
        
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
        
        return "Broadcasting started"
    
    def stop_broadcasting(self):
        """Stop autonomous broadcasting"""
        self.is_running = False
        return "Broadcasting stopped"
    
    def _run_scheduler(self):
        """Run the scheduler in background"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def broadcast_market_update(self):
        """Create and broadcast market update"""
        try:
            # Get market data
            spy = yf.Ticker("SPY")
            info = spy.info
            price = info.get('regularMarketPrice', 0)
            change = info.get('regularMarketChangePercent', 0)
            
            # Create message
            sentiment = "🟢 BULLISH" if change > 0 else "🔴 BEARISH"
            message = f"""📊 MARKET UPDATE - {datetime.now().strftime('%H:%M')}
            
S&P 500: ${price:.2f} ({change:+.2f}%)
Market Sentiment: {sentiment}
AI Confidence: {min(95, abs(change)*20 + 60):.0f}%

#MarketUpdate #Stocks #Trading #SP500"""
            
            # Broadcast to all platforms
            self.social_streamer.stream_to_all(
                data={'symbol': 'SPY'},
                message=message,
                image_path=self.create_market_chart('SPY')
            )
            
        except Exception as e:
            print(f"Market update error: {e}")
    
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
                top_movers.append(f"{symbol}: {change:+.1f}%")
            
            message = f"""🚀 TOP MOVERS {datetime.now().strftime('%H:%M')}
            
{' | '.join(top_movers)}

Biggest gainers today: Check your watchlist!

#TopMovers #StockMarket #Gainers #Losers"""
            
            self.social_streamer.stream_to_all(
                data={'symbol': 'MARKET'},
                message=message
            )
            
        except Exception as e:
            print(f"Top movers error: {e}")
    
    def broadcast_sector_analysis(self):
        """Broadcast sector performance analysis"""
        try:
            sectors = {
                'XLK': 'Tech', 'XLF': 'Financials', 'XLV': 'Healthcare',
                'XLE': 'Energy', 'XLI': 'Industrials', 'XLU': 'Utilities'
            }
            
            sector_performance = []
            for etf, name in sectors.items():
                ticker = yf.Ticker(etf)
                info = ticker.info
                change = info.get('regularMarketChangePercent', 0)
                emoji = "🟢" if change > 0 else "🔴"
                sector_performance.append(f"{emoji} {name}: {change:+.1f}%")
            
            message = f"""📈 SECTOR ANALYSIS {datetime.now().strftime('%H:%M')}
            
{' | '.join(sector_performance)}

Strongest: {sectors[max(sectors, key=lambda x: yf.Ticker(x).info.get('regularMarketChangePercent', 0))]}
Weakest: {sectors[min(sectors, key=lambda x: yf.Ticker(x).info.get('regularMarketChangePercent', 0))]}

#SectorAnalysis #MarketTrends #TradingStrategy"""
            
            self.social_streamer.stream_to_all(
                data={'symbol': 'SECTORS'},
                message=message
            )
            
        except Exception as e:
            print(f"Sector analysis error: {e}")
    
    def broadcast_trading_alerts(self):
        """Broadcast active trading alerts"""
        try:
            # Get top 3 alerts from global alerts
            alerts = self.get_active_alerts()
            
            if alerts:
                message = f"""🚨 TRADING ALERTS {datetime.now().strftime('%H:%M')}
                
"""
                for alert in alerts[:3]:
                    emoji = "🟢" if "BUY" in alert['type'] else "🔴"
                    message += f"{emoji} {alert['symbol']}: {alert['type']} @ ${alert['price']:.2f}\n   Confidence: {alert['confidence']}%\n\n"
                
                message += "#TradingAlerts #StockSignals #AITrading"
                
                self.social_streamer.stream_to_all(
                    data={'symbol': 'ALERTS'},
                    message=message
                )
            
        except Exception as e:
            print(f"Trading alerts error: {e}")
    
    def broadcast_daily_summary(self):
        """Broadcast daily market summary"""
        try:
            # Get daily performance
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1d")
            
            if not hist.empty:
                open_price = hist['Open'].iloc[0]
                close_price = hist['Close'].iloc[-1]
                day_change = ((close_price - open_price) / open_price * 100)
                
                message = f"""📊 DAILY MARKET SUMMARY - {datetime.now().strftime('%Y-%m-%d')}
                
S&P 500: ${close_price:.2f} ({day_change:+.2f}%)
Day Range: ${hist['Low'].min():.2f} - ${hist['High'].max():.2f}
Volume: {hist['Volume'].sum():,}

Top Performers: Tech & Financials
AI Prediction: {'Bullish' if day_change > 0 else 'Bearish'}

#DailySummary #MarketWrap #TradingRecap"""
                
                # Create video summary
                video_path = self.create_summary_video(spy, day_change)
                
                self.social_streamer.stream_to_all(
                    data={'symbol': 'DAILY'},
                    message=message,
                    video_path=video_path
                )
            
        except Exception as e:
            print(f"Daily summary error: {e}")
    
    def create_market_chart(self, symbol):
        """Create chart image for broadcasting"""
        try:
            import matplotlib.pyplot as plt
            
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d", interval="5m")
            
            if not hist.empty:
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
            
        except:
            return None
    
    def create_summary_video(self, stock_data, day_change):
        """Create video summary for daily broadcast"""
        try:
            # Create text-based video
            text = f"Market Summary\n{datetime.now().strftime('%Y-%m-%d')}\n\nS&P 500: {day_change:+.2f}%\n\nAI Analysis: {'Bullish' if day_change > 0 else 'Bearish'}"
            
            tts = gTTS(text)
            audio_path = tempfile.mktemp(suffix=".mp3")
            tts.save(audio_path)
            
            # Create video clip
            txt_clip = TextClip(text, fontsize=40, color='white', font='Arial', size=(1080, 1920))
            txt_clip = txt_clip.set_duration(15).set_position('center')
            
            video_path = tempfile.mktemp(suffix=".mp4")
            txt_clip.write_videofile(video_path, fps=24)
            
            return video_path
            
        except:
            return None
    
    def get_active_alerts(self):
        """Get active trading alerts"""
        # This would connect to your main app's alerts
        # For demo, return sample alerts
        return [
            {'symbol': 'AAPL', 'type': 'BUY', 'price': 175.50, 'confidence': 85},
            {'symbol': 'TSLA', 'type': 'STRONG BUY', 'price': 240.30, 'confidence': 92},
            {'symbol': 'NVDA', 'type': 'HOLD', 'price': 890.20, 'confidence': 65},
        ]

class ContentScheduler:
    """Advanced content scheduling system"""
    
    def __init__(self):
        self.schedule = {
            'market_open': ['market_update', 'top_movers'],
            'mid_morning': ['sector_analysis', 'trading_alerts'],
            'lunch': ['market_update', 'educational_tip'],
            'afternoon': ['top_movers', 'trading_alerts'],
            'market_close': ['daily_summary', 'preview_tomorrow'],
            'evening': ['recap_video', 'sentiment_analysis']
        }
        
    def get_content_for_time(self):
        """Get content type based on current time"""
        hour = datetime.now().hour
        
        if 9 <= hour < 12:
            return self.schedule['market_open']
        elif 12 <= hour < 14:
            return self.schedule['mid_morning']
        elif 14 <= hour < 16:
            return self.schedule['lunch']
        elif 16 <= hour < 20:
            return self.schedule['afternoon']
        elif 20 <= hour < 22:
            return self.schedule['market_close']
        else:
            return self.schedule['evening']
