import asyncio
from dataclasses import dataclass, field

import aiohttp
from discord.app_commands import Choice


@dataclass(frozen=True, eq=True)
class LyricResult:
    title: str = None
    artist: str = None
    lyrics: str = None
    images: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def empty():
        return LyricResult()


@dataclass(frozen=True, eq=True)
class LyricAutocompleteSuggestions:
    title: str
    artists: list[str] = field(default_factory=list)

    def __str__(self):
        return f"{self.title} - {', '.join(self.artists)}"


class Lyrics:
    CACHE = {}
    URL = "https://api.yodabot.xyz/v/{}/lyrics"  # Use Yoda API

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

        async with self.session.get(self.url + '/search', params=params) as resp:
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

    async def autocomplete(self, query: str, amount: int = 10, *, slash_autocomplete: bool = False):
        if 1 > amount or amount > 20:
            raise ValueError("Amount must be between 1 and 20")

        params = {'q': query, 'amount': amount}

        async with self.session.get(self.url + '/suggest', params=params) as resp:
            d = await resp.json()

        suggestions = [LyricAutocompleteSuggestions(**suggestion) for suggestion in d]

        if slash_autocomplete:
            return [Choice(name=str(suggestion), value=str(suggestion)) for suggestion in suggestions]

        return suggestions
