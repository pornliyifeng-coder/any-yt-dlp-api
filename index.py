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

def parse_cookies(cookie_str: str, temp_file_path: str):
    """将字符串 Cookie 转换为 Netscape 格式文件"""
    with open(temp_file_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                # 为 YouTube 强制关联域名，确保 Cookie 生效
                f.write(f'.youtube.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n')

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: Optional[str] = Header(None)):
    # 验证 API Key (保持您原有的逻辑)
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")

    temp_cookie_file = None
    try:
        ydl_opts = {
            # 🚀 核心优化：优先请求单文件 MP4 格式，避开需要 FFmpeg 合并的 DASH 流
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            # 💡 强制使用这些客户端可以提高解析成功率，避开部分限制
            'player_client': ['tv', 'mweb'], 
        }

        if req.cookies:
            fd, temp_cookie_file = tempfile.mkstemp()
            os.close(fd)
            parse_cookies(req.cookies, temp_cookie_file)
            ydl_opts['cookiefile'] = temp_cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            
            # 返回 App 预期的字段名
            return {
                "url": info.get('url') or info.get('webpage_url'),
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
