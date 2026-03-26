load_dotenv()

AYSHARE = SocialPostAPI(os.getenv("AYSHARE_API_KEY"))
STOCKS = ["AAPL", "TSLA", "NVDA", "GOOGL", "AMZN", "MSFT"]

# ------------------- NEW: VERTICAL VIDEO FOR TIKTOK/REELS -------------------
def generate_video(symbol: str, orientation="horizontal"):
    info = get_stock_data(symbol)
    pred = get_prediction(info)
   
    # Choose size
    if orientation == "vertical":
        size = (1080, 1920)
        title = f"🚨 {symbol} AI ALERT"
    else:
        size = (1920, 1080)
        title = f"{symbol} Live • AI Prediction"

    # Create chart
    data = yf.download(symbol, period="1d", interval="5m")
    plt.figure(figsize=(size[0]/100, size[1]/100), dpi=100)
    plt.plot(data['Close'], label="Price", color="#00ff88", linewidth=6)
    plt.title(f"{symbol} ${info['price']} | {pred['signal']}", fontsize=60, color="white")
    plt.gca().set_facecolor("#111111")
    plt.legend(fontsize=40)
    chart_path = f"charts/temp_{symbol}_{orientation}.png"
    plt.savefig(chart_path, bbox_inches='tight', facecolor="#111111")
    plt.close()

    # AI voice
    text = f"{symbol} is now at ${info['price']}. Our AI says {pred['signal']}. Reason: {pred['reason']}. This is not financial advice. Always do your own research."
    tts = gTTS(text)
    audio_path = f"charts/temp_{symbol}_{orientation}.mp3"
    tts.save(audio_path)

    # Video
    img_clip = ImageClip(chart_path).set_duration(15).resize(size)
    txt_clip = TextClip(title, fontsize=90, color='red', font='Arial-Bold').set_position('center').set_duration(15)
    video = CompositeVideoClip([img_clip, txt_clip])
    video = video.set_audio(audio_path)

    video_path = f"videos/{symbol}_{orientation}_{datetime.now().strftime('%Y%m%d_%H%M')}.mp4"
    video.write_videofile(video_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
    os.remove(chart_path)
    os.remove(audio_path)
    return video_path

# ------------------- AUTONOMOUS POSTING -------------------
def post_to_all_platforms(video_horizontal: str, video_vertical: str, symbol: str, info: dict, pred: dict):
    caption = f"""
{symbol} LIVE • ${info['price']} ({'+' if info['change']>0 else ''}{info['change']}%)
AI Prediction: {pred['signal']} — {pred['reason']}
Not financial advice • DYOR
#Stocks #{symbol} #AI
    """.strip()

    # 1. Ayrshare → posts to EVERY platform at once
    try:
        response = AYSHARE.post(
            post= caption,
            platforms=["youtube", "tiktok", "instagram", "twitter", "linkedin", "facebook", "reddit", "pinterest", "telegram"],
            mediaUrls=[video_horizontal],           # YouTube & others use horizontal
            mediaUrlsVertical=[video_vertical] if video_vertical else None,  # TikTok/Reels/Shorts
            title=f"{symbol} AI Stock Alert",
            youtubeTitle=f"{symbol} LIVE - AI says {pred['signal']}",
            isShorts=True if "youtube" in response else False
        )
        print(f"✅ Ayrshare posted {symbol} to ALL platforms!")
        print(response)
    except Exception as e:
        print("Ayrshare failed, falling back to direct YouTube + TikTok...")

        # 2. Direct YouTube fallback
        try:
            youtube_upload(video_horizontal, symbol, info, pred)
        except: pass

        # 3. TikTok fallback (cookie-based)
        try:
            tiktok_uploader.uploadVideo(
                session_id=os.getenv("TIKTOK_SESSIONID"),
                file=video_vertical,
                title=f"{symbol} AI says {pred['signal']}",
                tags=["Stocks", symbol, "AI", "fyp"]
            )
        except: pass

def youtube_upload(video_path: str, symbol: str, info: dict, pred: dict):
    # One-time OAuth flow (runs only first time)
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secrets.json", scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds = flow.run_local_server(port=8080)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": f"{symbol} LIVE • AI Prediction ${info['price']}",
            "description": f"AI says {pred['signal']}\n\nNot financial advice.",
            "tags": [symbol, "stocks", "AI", "finance"],
            "categoryId": "25"  # News & Politics
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = request.execute()
    print(f"✅ YouTube upload success → https://youtu.be/{response['id']}")

# ------------------- BACKGROUND JOB (every 5 min) -------------------
async def auto_generate_content():
    print(f"[{datetime.now()}] 🚀 Generating + posting new content...")
    for symbol in STOCKS[:2]:   # limit to 2 per cycle
        try:
            info = get_stock_data(symbol)
            pred = get_prediction(info)
           
            horiz = generate_video(symbol, "horizontal")
            vert = generate_video(symbol, "vertical")
           
            post_to_all_platforms(horiz, vert, symbol, info, pred)
           
            # Optional: delete old videos to save disk
            os.remove(horiz)
            os.remove(vert)
        except Exception as e:
            print(f"Error with {symbol}: {e}")

# (rest of your old main.py stays exactly the same — scheduler, API routes, frontend unchanged) 
