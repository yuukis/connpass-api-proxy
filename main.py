from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
import os
import httpx

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")

app = FastAPI()


@app.get("/{tail:path}")
async def proxy_connpass(request: Request, tail: str):
    params = dict(request.query_params)
    headers = {
        "X-API-Key": API_KEY
    }
    url = f"{BASE_URL}/{tail}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if response.status_code == 200:
        return JSONResponse(status_code=200, content=response.json())

    return Response(status_code=response.status_code, content=response.content)
