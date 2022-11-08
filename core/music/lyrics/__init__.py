import asyncio
from dataclasses import dataclass, field

import aiohttp


@dataclass(frozen=True, eq=True)
class LyricResult:
    title: str = None
    artist: str = None
    lyrics: str = None
    images: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def empty():
        return LyricResult()


class Lyrics:
    CACHE = {}
    URL = "https://api.yodabot.xyz/v/{}/lyrics/search"  # Use Yoda API

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, session: aiohttp.ClientSession = None,
                 api_version='latest'):
        self.session: aiohttp.ClientSession = session or aiohttp.ClientSession()

        self.url = self.URL.format(api_version)  # Yoda API latest

        self.loop = loop or asyncio.get_event_loop()

        self.CACHE_TTL_TASKS = []

    async def __call__(self, query: str, *, cache: bool = True, get_from_cache: bool | None = None):
        return self.search(query, cache=cache, get_from_cache=get_from_cache)

    def set_cache(self, key, value, ttl=None):
        self.CACHE[key] = value

        async def task():
            while True:
                await asyncio.sleep(ttl)
                self.CACHE.pop(key)

        if ttl is not None:
            self.CACHE_TTL_TASKS.append(self.loop.create_task(task()))

    def get_cache(self, key):
        return self.CACHE.get(key)

    async def call_api(self, query: str) -> dict:
        params = {'q': query}

        async with self.session.get(self.url, params=params) as resp:
            d = await resp.json()

        return d

    async def search(self, query: str, *, cache: bool = True, get_from_cache: bool | None = None):
        q_lower = query.lower()

        if (cached := self.get_cache(q_lower)) and get_from_cache is not False:
            return cached

        if get_from_cache is True:
            return LyricResult.empty()

        data = await self.call_api(query)

        res = LyricResult(**data)

        if not res.lyrics:
            return LyricResult.empty()

        if cache:
            self.set_cache(q_lower, res)

        return res
