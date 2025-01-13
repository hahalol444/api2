from fastapi import FastAPI, HTTPException
import httpx
from contextlib import asynccontextmanager
from time import time
import uvicorn

app = FastAPI()

server_cache = {}
rate_limit_timers = {}

@asynccontextmanager
async def get_client():
    async with httpx.AsyncClient() as client:
        yield client

async def get_game_thumbnails():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive"
    }

    cache_key = "thumbnails_request"
    cache_entry = server_cache.get(cache_key)
    current_time = time()

    rate_limit_end = rate_limit_timers.get(cache_key, 0)
    if current_time < rate_limit_end:
        print(f"[Rate Limited] Using cached data ({int(rate_limit_end - current_time)}s remaining)")
        if cache_entry:
            return cache_entry['data']
        raise HTTPException(status_code=429, detail="Rate limited and no cached data available")

    if cache_entry and (current_time - cache_entry['timestamp'] < 10):
        print(f"[Cache Hit] Returning cached data ({int(10 - (current_time - cache_entry['timestamp']))}s remaining)")
        return cache_entry['data']

    try:
        print("[Fetching] Getting new thumbnail data...")
        url = "https://thumbnails.roblox.com/v1/batch"
        payload = [
            {
                "requestId": "example_request_id",
                "type": "AvatarHeadShot",
                "token": "example_token",
                "size": "150x150"
            }
        ]

        async with get_client() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    server_cache[cache_key] = {
                        'data': data,
                        'timestamp': current_time
                    }
                    print("[Success] Found thumbnail data")
                    return data
                print("[Empty] No thumbnail data found")
                raise HTTPException(status_code=404, detail="No thumbnail data found")

            if response.status_code == 404:
                print("[Not Found] Endpoint does not exist")
                raise HTTPException(status_code=404, detail="Endpoint not found")

            if response.status_code == 429:
                print("[Rate Limited] Using cached data")
                rate_limit_timers[cache_key] = current_time + 60

                if cache_entry:
                    return cache_entry['data']
                raise HTTPException(status_code=429, detail="Rate limited and no cached data available")

    except Exception as e:
        print("[Error] Failed to fetch thumbnail data, using cached data if available")

        if cache_entry:
            return cache_entry['data']
        raise HTTPException(status_code=500, detail="Unable to fetch thumbnail data. Please try again.")

@app.get("/thumbnails")
async def get_thumbnails():
    return await get_game_thumbnails()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
