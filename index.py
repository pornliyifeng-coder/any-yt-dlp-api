from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import yt_dlp
import os
import tempfile
from urllib.parse import urlparse

app = FastAPI()

class ExtractReq(BaseModel):
    url: str
    cookies: str = None

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: str = Header(None)):
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 🚀 极简兼容模式：不强制格式，让引擎先拿到数据
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # 不写 'format' 键，让 yt-dlp 内部默认处理
    }

    tmp_path = None
    if req.cookies and len(req.cookies) > 10:
        try:
            domain = urlparse(req.url).netloc
            if domain.startswith("m."): domain = domain[2:]
            if domain.startswith("www."): domain = domain[4:]
            
            fd, tmp_path = tempfile.mkstemp(suffix=".txt")
            with os.fdopen(fd, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                pairs = req.cookies.split(';')
                for pair in pairs:
                    if '=' in pair:
                        name, value = pair.strip().split('=', 1)
                        f.write(f".{domain}\tTRUE\t/\tTRUE\t2147483647\t{name}\t{value}\n")
            ydl_opts['cookiefile'] = tmp_path
        except Exception as e:
            print(f"❌ [Backend] Cookie Error: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 💡 关键：download=False 只获取元数据
            info = ydl.extract_info(req.url, download=False)
            
            # 手动挑选最佳可播放链接
            play_url = None
            
            # 策略 1：直接获取主 URL
            if info.get('url'):
                play_url = info.get('url')
            
            # 策略 2：如果主 URL 不行，从 formats 里挑一个（音画合一的或 HLS）
            if not play_url and 'formats' in info:
                # 寻找合并流
                formats = info['formats']
                
                # 1. 优先寻找 HLS (m3u8) - iOS 播放器的最爱
                hls_streams = [f for f in formats if 'm3u8' in (f.get('protocol') or '') or f.get('ext') == 'm3u8']
                if hls_streams:
                    play_url = hls_streams[-1].get('url') # 取最高画质的 HLS
                
                # 2. 次选：包含音视频的 MP4
                if not play_url:
                    mp4_combined = [f for f in formats if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                    if mp4_combined:
                        play_url = mp4_combined[-1].get('url')

            if not play_url:
                raise Exception("No playable combined stream found")

            return {
                "title": info.get('title'),
                "play_url": play_url,
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [Backend] Final Extraction failed: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "yt-dlp"}
