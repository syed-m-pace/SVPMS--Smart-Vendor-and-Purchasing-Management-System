from __future__ import annotations
# api/services/cache.py
import httpx
import json
from api.config import settings


class UpstashClient:
    def __init__(self):
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    async def get(self, key: str) -> str | None:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{self.url}/get/{key}", headers=self.headers)
            return r.json().get("result")

    async def set(self, key: str, value: str, ex: int = 300):
        async with httpx.AsyncClient() as c:
            await c.get(f"{self.url}/set/{key}/{value}/ex/{ex}", headers=self.headers)

    async def incr(self, key: str) -> int:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{self.url}/incr/{key}", headers=self.headers)
            return r.json().get("result", 0)

    async def expire(self, key: str, seconds: int):
        async with httpx.AsyncClient() as c:
            await c.get(
                f"{self.url}/expire/{key}/{seconds}", headers=self.headers
            )

    async def pipeline(self, commands: list[list]) -> list:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{self.url}/pipeline", headers=self.headers, json=commands
            )
            return r.json()

    async def delete(self, key: str):
        async with httpx.AsyncClient() as c:
            await c.get(f"{self.url}/del/{key}", headers=self.headers)


cache = UpstashClient()
