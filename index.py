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
    
    # 🚀 修正配置：拥抱 HLS，模拟移动端环境
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # 允许所有格式，优先选择已经合并好的最佳流 (通常是 m3u8 或 mp4)
        'format': 'best', 
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb']
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
                pairs = req.cookies.split(';')
                for pair in pairs:
                    if '=' in pair:
                        name, value = pair.strip().split('=', 1)
                        f.write(f".{domain}\tTRUE\t/\tTRUE\t2147483647\t{name}\t{value}\n")
            ydl_opts['cookiefile'] = tmp_path
        except Exception as e:
            print(f"❌ [Backend] Cookie generation failed: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            
            # 优先获取直链
            play_url = info.get('url')
            
            # 如果没有主 URL，说明是多流格式，我们遍历 formats 寻找一个合并好的流
            if not play_url and 'formats' in info:
                # 寻找支持的流：1. m3u8 2. 包含音画的 mp4
                valid_formats = [f for f in info['formats'] if (f.get('vcodec') != 'none' and f.get('acodec') != 'none') or f.get('protocol') == 'm3u8_native']
                if valid_formats:
                    # 优先取 m3u8，因为它在 iOS 上最稳定
                    hls_formats = [f for f in valid_formats if 'm3u8' in (f.get('protocol') or '')]
                    if hls_formats:
                        play_url = hls_formats[-1].get('url') # 取最高清晰度的 HLS
                    else:
                        play_url = valid_formats[-1].get('url')

            return {
                "title": info.get('title'),
                "play_url": play_url,
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [Backend] Extraction failed: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "yt-dlp"}
