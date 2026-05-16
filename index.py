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
            # 🚀 优先寻找可直接播放的单文件格式
            'format': '18/22/best',
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            # 🚀 绕过 n-challenge 加密的关键：强行使用 Android/iOS 客户端
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],
                }
            },
            'user_agent': req.user_agent or 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        }

        if req.cookies:
            fd, temp_cookie_file = tempfile.mkstemp()
            os.close(fd)
            parse_cookies(req.cookies, temp_cookie_file)
            ydl_opts['cookiefile'] = temp_cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            if not info:
                raise Exception("yt-dlp returned no info")
                
            # 智能查找有效播放地址
            stream_url = info.get('url')
            if not stream_url and 'formats' in info:
                # 倒序查找，通常后面的质量更好
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') != 'none':
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
