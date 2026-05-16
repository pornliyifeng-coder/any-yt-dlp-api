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
            'format': 'best',
            # 🚀 绝招：强制使用 IPv4，避开 YouTube 对 Vercel IPv6 的严厉封锁
            'source_address': '0.0.0.0', 
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            # 模拟安卓 YouTube App
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
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
                raise Exception("yt-dlp returned no info")
                
            stream_url = info.get('url')
            if not stream_url and 'formats' in info:
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
