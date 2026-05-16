from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import yt_dlp
import os
import tempfile
import sys

app = FastAPI()

class ExtractReq(BaseModel):
    url: str
    cookies: Optional[str] = None
    user_agent: Optional[str] = None

def parse_cookies(cookie_str: str, temp_file_path: str):
    """更严格的 Netscape 格式生成"""
    with open(temp_file_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                parts = cookie.strip().split('=', 1)
                if len(parts) == 2:
                    name, value = parts
                    # 使用标准 Tab 分隔符，并确保包含 7 个字段
                    # 域名, 子域名可用, 路径, 安全, 过期时间, 名称, 值
                    f.write(f'.youtube.com\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}\n')

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: Optional[str] = Header(None)):
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")

    temp_cookie_file = None
    try:
        ydl_opts = {
            'format': 'best', # 还原为最稳的 best，让服务器自己选
            'quiet': False,   # 🚀 开启日志，方便调试
            'no_warnings': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'user_agent': req.user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        if req.cookies:
            fd, temp_cookie_file = tempfile.mkstemp()
            os.close(fd)
            parse_cookies(req.cookies, temp_cookie_file)
            ydl_opts['cookiefile'] = temp_cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 🚀 尝试获取信息
            try:
                info = ydl.extract_info(req.url, download=False)
            except Exception as ydl_err:
                # 捕获 yt-dlp 内部的明确报错
                raise HTTPException(status_code=500, detail=f"yt-dlp error: {str(ydl_err)}")
                
            if not info:
                raise HTTPException(status_code=500, detail="yt-dlp returned empty info")

            # 提取地址逻辑
            url = info.get('url')
            if not url and 'formats' in info:
                # 找一个有直链的格式
                valid_formats = [f for f in info['formats'] if f.get('url')]
                if valid_formats:
                    # 优先找 MP4，否则找最后一个（通常是质量最好的）
                    url = next((f['url'] for f in valid_formats if f.get('ext') == 'mp4'), valid_formats[-1]['url'])

            return {
                "url": url or info.get('webpage_url'),
                "title": info.get('title'),
                "poster": info.get('thumbnail'),
                "duration": info.get('duration')
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            os.remove(temp_cookie_file)

@app.get("/")
async def root():
    return {"status": "Any-YT-DLP API is running"}
