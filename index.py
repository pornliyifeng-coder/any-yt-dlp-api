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
    
    # 🚀 终极模式：模拟各种环境并强制获取任意可用流
    ydl_opts = {
        'quiet': False, # 开启日志以便在 Vercel 控制台查看
        'no_warnings': False,
        'nocheckcertificate': True,
        'format': 'best', # 强制要求最好的单文件
        'ignoreerrors': True,
        'no_color': True,
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'referer': 'https://www.youtube.com/',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web'],
                'player_skip': ['webpage', 'configs']
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
            # 1. 尝试直接获取
            info = ydl.extract_info(req.url, download=False)
            
            if not info:
                raise Exception("Failed to extract info (YouTube might be blocking the IP)")

            play_url = info.get('url')
            
            # 2. 如果没有直接 URL，手动从 formats 列表打捞
            if not play_url and 'formats' in info:
                formats = info['formats']
                # 寻找任何非音画分离的格式
                valid = [f for f in formats if f.get('url') and (f.get('vcodec') != 'none' and f.get('acodec') != 'none')]
                if not valid:
                    # 如果连合并流都没有，尝试拿 HLS
                    valid = [f for f in formats if f.get('protocol') == 'm3u8_native' or 'm3u8' in f.get('url', '')]
                
                if valid:
                    # 选一个清晰度适中的（防止流量过大或加载慢）
                    play_url = valid[-1].get('url')

            if not play_url:
                # 打印所有格式 ID 供调试
                format_ids = [f.get('format_id') for f in info.get('formats', [])]
                raise Exception(f"No playable URL found. Available formats: {format_ids}")

            return {
                "title": info.get('title'),
                "play_url": play_url,
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [Backend] Fatal Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "yt-dlp"}
