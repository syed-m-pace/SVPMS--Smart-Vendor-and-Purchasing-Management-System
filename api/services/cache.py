from __future__ import annotations
# api/services/cache.py
import httpx
import json
from api.config import settings

# Module-level singleton — avoids creating a new TLS connection on every Redis call.
_http = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=30)
)


class UpstashClient:
    def __init__(self):
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    async def get(self, key: str) -> str | None:
        r = await _http.get(f"{self.url}/get/{key}", headers=self.headers)
        return r.json().get("result")

    async def set(self, key: str, value: str, ex: int = 300):
        await _http.get(f"{self.url}/set/{key}/{value}/ex/{ex}", headers=self.headers)

    async def incr(self, key: str) -> int:
        r = await _http.get(f"{self.url}/incr/{key}", headers=self.headers)
        return r.json().get("result", 0)

    async def expire(self, key: str, seconds: int):
        await _http.get(
            f"{self.url}/expire/{key}/{seconds}", headers=self.headers
        )

    async def pipeline(self, commands: list[list]) -> list:
        r = await _http.post(
            f"{self.url}/pipeline", headers=self.headers, json=commands
        )
        return r.json()

    async def delete(self, key: str):
        await _http.get(f"{self.url}/del/{key}", headers=self.headers)

    async def setnx(self, key: str, value: str, ex: int = 300) -> bool:
        """Set key only if it does not exist. Returns True if the key was set."""
        r = await _http.get(
            f"{self.url}/set/{key}/{value}/nx/ex/{ex}", headers=self.headers
        )
        result = r.json().get("result")
        return result == "OK"

    async def ping(self) -> bool:
        r = await _http.get(f"{self.url}/ping", headers=self.headers)
        return r.json().get("result") == "PONG"


cache = UpstashClient()
