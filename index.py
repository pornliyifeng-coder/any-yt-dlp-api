from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import yt_dlp
import os
import tempfile

app = FastAPI()

class ExtractReq(BaseModel):
    url: str
    cookies: str = None # 接收从 App 传来的 Cookie 字符串

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: str = Header(None)):
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'nocheckcertificate': True,
    }

    # 💡 关键：处理传入的 Cookies
    # 如果 App 传来了 Cookie 字符串，我们将其写入临时文件并交给 yt-dlp
    tmp_cookie_file = None
    if req.cookies and len(req.cookies) > 10:
        try:
            # 创建一个临时的 Netscape 格式 Cookie 文件或直接尝试通过 Header 传递
            # 这里我们简单地通过 HTTP Headers 传递，yt-dlp 支持这种方式
            ydl_opts['http_headers'] = {
                'Cookie': req.cookies,
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
            }
        except Exception as e:
            print(f"Cookie processing error: {e}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            return {
                "title": info.get('title'),
                "play_url": info.get('url'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
    except Exception as e:
        error_msg = str(e)
        print(f"Extraction error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "yt-dlp"}
