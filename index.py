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
    
    # 🚀 优化配置：模拟 iOS 客户端以获取最佳 M3U8 流
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # 优先选择 mp4 格式或 m3u8 格式
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web', 'mweb'],
                'skip': ['hls', 'dash'] # 有时跳过某些限制反而能拿到直链
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
            
            # 💡 逻辑优化：自动寻找最适合播放的 URL
            play_url = info.get('url')
            
            # 如果是最佳格式（音画分离），yt-dlp 在 download=False 时可能只返回 manifest
            # 我们尝试从 formats 列表里找一个单文件的直链
            if not play_url and 'formats' in info:
                # 过滤出包含音轨和视轨的格式 (acodec != none and vcodec != none)
                combined_formats = [f for f in info['formats'] if f.get('acodec') != 'none' and f.get('vcodec') != 'none']
                if combined_formats:
                    # 按照分辨率排序取最好的一个
                    best_f = sorted(combined_formats, key=lambda x: x.get('height') or 0, reverse=True)[0]
                    play_url = best_f.get('url')

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
