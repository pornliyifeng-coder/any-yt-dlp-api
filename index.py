from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import yt_dlp
import os

app = FastAPI()

class ExtractReq(BaseModel):
    url: str
    cookies: str = None

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: str = Header(None)):
    # 校验 API Key，与 App 端保持一致
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # yt-dlp 配置：只解析不下载，获取最佳画质直链
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 提取视频信息
            info = ydl.extract_info(req.url, download=False)
            
            # 返回给 App 识别的格式
            return {
                "title": info.get('title'),
                "play_url": info.get('url'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "yt-dlp"}

# 关键：Vercel 识别的入口
@app.get("/")
async def root():
    return {"message": "YT Extractor API is running on Vercel!"}
