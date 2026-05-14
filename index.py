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
    
    # 🚀 尝试 TV 协议：电视端协议风控较低，且支持 Cookie
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'format': 'best',
        'extractor_args': {
            'youtube': {
                # 强制使用 tv 客户端，它对云端 IP 相对友好
                'player_client': ['tv', 'mweb']
            }
        }
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
                for pair in req.cookies.split(';'):
                    if '=' in pair:
                        name, value = pair.strip().split('=', 1)
                        f.write(f".youtube.com\tTRUE\t/\tTRUE\t2147483647\t{name}\t{value}\n")
            ydl_opts['cookiefile'] = tmp_path
        except Exception as e:
            print(f"❌ [Backend] Cookie Error: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            
            if not info:
                raise Exception("YouTube blocked this request (IP or Challenge failure)")

            play_url = info.get('url')
            
            # 打捞逻辑
            if not play_url and 'formats' in info:
                formats = info['formats']
                # 寻找合并流或 HLS
                valid = [f for f in formats if f.get('url') and (f.get('vcodec') != 'none' and f.get('acodec') != 'none')]
                if not valid:
                    valid = [f for f in formats if f.get('protocol') == 'm3u8_native' or 'm3u8' in (f.get('url') or '')]
                
                if valid:
                    play_url = valid[-1].get('url')

            if not play_url:
                raise Exception("No playable stream found after TV/MWeb fallback")

            return {
                "title": info.get('title'),
                "play_url": play_url,
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [Backend] Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "yt-dlp"}
