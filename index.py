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
    user_agent: Optional[str] = None  # 🚀 新增：支持从 App 传入 UA

def parse_cookies(cookie_str: str, temp_file_path: str):
    """将字符串 Cookie 转换为 Netscape 格式文件"""
    with open(temp_file_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                parts = cookie.strip().split('=', 1)
                if len(parts) == 2:
                    name, value = parts
                    # 扩展域名覆盖，确保全站通用
                    f.write(f'.youtube.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n')

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: Optional[str] = Header(None)):
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")

    temp_cookie_file = None
    try:
        # 🌟 更加鲁棒的配置
        ydl_opts = {
            # 🚀 宽容的格式选择：18(360p MP4) -> 22(720p MP4) -> 任意最优
            'format': '18/22/best', 
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_color': True,
        }

        # 🚀 注入 App 端的 User-Agent，确保指纹一致
        if req.user_agent:
            ydl_opts['user_agent'] = req.user_agent

        if req.cookies:
            fd, temp_cookie_file = tempfile.mkstemp()
            os.close(fd)
            parse_cookies(req.cookies, temp_cookie_file)
            ydl_opts['cookiefile'] = temp_cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            if not info:
                raise Exception("Unable to extract info")
                
            # 💡 优先寻找直链地址
            stream_url = info.get('url')
            if not stream_url and 'formats' in info:
                # 如果 top-level 没有 url，从 formats 里找一个最匹配的
                for f in reversed(info['formats']):
                    if f.get('vcodec') != 'none' and f.get('url'):
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
