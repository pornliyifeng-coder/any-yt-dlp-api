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
    with open(temp_file_path, 'w') as f:
        f.write('# Netscape HTTP Cookie File\n')
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                parts = cookie.strip().split('=', 1)
                if len(parts) == 2:
                    name, value = parts
                    f.write(f'.youtube.com\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}\n')

def try_extract(url, ydl_opts):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except:
        return None

@app.post("/extract")
async def extract(req: ExtractReq, x_api_key: Optional[str] = Header(None)):
    if x_api_key != "Liyifeng11":
        raise HTTPException(status_code=401, detail="Unauthorized")

    temp_cookie_file = None
    try:
        if req.cookies:
            fd, temp_cookie_file = tempfile.mkstemp()
            os.close(fd)
            parse_cookies(req.cookies, temp_cookie_file)

        # 🚀 尝试不同的配置组合
        strategies = [
            {'player_client': ['android'], 'ua': 'com.google.android.youtube/19.14.34 (Linux; U; Android 11) gzip'},
            {'player_client': ['ios'], 'ua': 'com.google.ios.youtube/19.14.34 (iPhone14,3; U; CPU iOS 17_0 like Mac OS X)'},
            {'player_client': ['mweb'], 'ua': req.user_agent},
            {'player_client': ['web'], 'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
        ]

        info = None
        last_error = "No strategies succeeded"

        for strategy in strategies:
            ydl_opts = {
                'format': 'best',
                'source_address': '0.0.0.0', # 强制 IPv4
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'extractor_args': {'youtube': {'player_client': strategy['player_client']}},
                'user_agent': strategy['ua'],
                'cookiefile': temp_cookie_file if temp_cookie_file else None
            }
            
            info = try_extract(req.url, ydl_opts)
            if info:
                break
        
        if not info:
            raise Exception("All extraction strategies failed. YouTube might be blocking the server IP.")

        # 提取结果 (保持原有逻辑)
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
