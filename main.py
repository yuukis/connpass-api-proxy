from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
import asyncio
import os
import httpx
import time
import hashlib
import json

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
ALLOWED_API_KEYS = set(os.getenv("ALLOWED_API_KEYS", "").split(","))

CACHE_TTL = 60
cache = {}

last_connpass_call = 0
connpass_lock = asyncio.Lock()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_cache_key(path: str, params: dict) -> str:
    key_data = {
        "path": path,
        "params": params
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()


@app.get("/{tail:path}")
async def proxy_connpass(request: Request, tail: str):
    user_api_key = request.headers.get("X-API-Key")
    if not user_api_key or user_api_key not in ALLOWED_API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")

    params = dict(request.query_params)
    headers = {
        "X-API-Key": API_KEY
    }
    url = f"{BASE_URL}/{tail}"

    cache_key = make_cache_key(url, params)
    now = time.time()
    if cache_key in cache:
        cached = cache[cache_key]
        if now - cached["time"] < CACHE_TTL:
            return JSONResponse(status_code=200, content=cached["data"])

    async with connpass_lock:
        global last_connpass_call
        wait_time = max(0, last_connpass_call + 1 - now)
        if wait_time > 0:
            print(f"Waiting for {wait_time} seconds to avoid rate limit")
            await asyncio.sleep(wait_time)
        last_connpass_call = time.time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))

    if response.status_code == 200:
        data = response.json()
        cache[cache_key] = {
            "time": now,
            "data": data
        }
        return JSONResponse(status_code=200, content=data)

    return Response(status_code=response.status_code, content=response.content)
