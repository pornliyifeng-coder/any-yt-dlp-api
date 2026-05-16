from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import yt_dlp
import os
import tempfile

app = FastAPI()

class ExtractReq(BaseModel):
    url: str
    cookies: Optional[str] = None
    user_agent: Optional[str] = None

def parse_cookies(cookie_str: str, temp_file_path: str):
    """生成 Netscape 格式 Cookie 文件"""
    with open(temp_file_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                parts = cookie.strip().split('=', 1)
                if len(parts) == 2:
                    name, value = parts
                    f.write(f'.youtube.com\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}\n')

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: Optional[str] = Header(None)):
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")

    temp_cookie_file = None
    try:
        ydl_opts = {
            # 🚀 既然服务器没 ffmpeg，我们就要最稳的单文件
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            # 🚀 核心：彻底模拟 Android 客户端，避开网页端的各种挑战和封锁
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'skip': ['hls', 'dash']
                }
            },
            # 使用安卓 YouTube App 的 User-Agent
            'user_agent': 'com.google.android.youtube/19.14.34 (Linux; U; Android 11) gzip'
        }

        if req.cookies:
            fd, temp_cookie_file = tempfile.mkstemp()
            os.close(fd)
            parse_cookies(req.cookies, temp_cookie_file)
            ydl_opts['cookiefile'] = temp_cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            if not info:
                raise Exception("Empty info returned from yt-dlp")
                
            stream_url = info.get('url')
            # 如果没拿到直链，去 formats 列表里搜刮一下
            if not stream_url and 'formats' in info:
                # 找一个 ext 是 mp4 且有 url 的
                for f in reversed(info['formats']):
                    if f.get('url') and (f.get('ext') == 'mp4' or f.get('vcodec') != 'none'):
                        stream_url = f['url']
                        break

            return {
                "url": stream_url or info.get('webpage_url'),
                "title": info.get('title'),
                "poster": info.get('thumbnail'),
                "duration": info.get('duration')
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            os.remove(temp_cookie_file)

@app.get("/")
async def root():
    return {"status": "Any-YT-DLP API is running"}
