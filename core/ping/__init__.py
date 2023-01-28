from __future__ import annotations

import time
from typing import TYPE_CHECKING

import aiohttp
import asyncpg
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Bot


class APIPing:
    URLS = {
        "yodabot": "https://api.yodabot.xyz/_health_check",
    }

    def __init__(self, ping: "Ping"):
        self._ping = ping

    async def yodabot(self, format: str = "ms") -> int | float:
        # API ping test, the fastest endpoint to test as it just returns a static text.
        url = self.URLS['yodabot']

        start = time.perf_counter()
        async with self._ping._bot.session.get(url) as resp:
            end = time.perf_counter()

            match format.lower():
                case "ms" | "milliseconds" | "millisecond":
                    return (end - start) * 1000
                case _:
                    return end - start

class Ping:
    EMOJIS = {
        "postgresql": "<:postgresql:903286241066385458>",
        "redis": "<:redis:903286716058710117>",
        "bot": "\U0001f916",
        "discord": "<:BlueDiscord:842701102381269022>",
        "typing": "<a:typing:597589448607399949>",
        "yodabot-api": "<:yoda:1041177124784054333>",
        "r2": "<:r2white:976076378854260749>"
    }

    URLS = {
        "discord": "https://discordapp.com/",
        "r2": "https://cdn.yodabot.xyz/"
    }

    def __init__(self, bot: Bot):
        self._bot = bot
        self._api_ping = APIPing(self)

    @property
    def api(self):
        return self._api_ping

    def bot(self, format: str = "ms") -> int | float:
        latency = self._bot.latency

        match format.lower():
            case "ms" | "milliseconds" | "millisecond":
                return latency * 1000
            case _:
                return latency

    async def discord(self, format: str = "ms") -> int | float:
        url = self.URLS['discord']

        start = time.perf_counter()
        async with self._bot.session.get(url) as resp:
            end = time.perf_counter()

            match format.lower():
                case "ms" | "milliseconds" | "millisecond":
                    return (end - start) * 1000
                case _:
                    return end - start

    async def typing(self, format: str = "ms") -> int | float:
        chan = self._bot.get_channel(903282453735678035)  # Typing Channel ping test

        start = time.perf_counter()
        await chan.typing()
        end = time.perf_counter()

        match format.lower():
            case "ms" | "milliseconds" | "millisecond":
                return (end - start) * 1000
            case _:
                return end - start

    async def r2(self, format: str = "ms") -> int | float:
        url = self.URLS['r2']

        start = time.perf_counter()
        async with self._bot.session.get(url) as resp:
            end = time.perf_counter()

        match format.lower():
            case "ms" | "milliseconds" | "millisecond":
                return (end - start) * 1000
            case _:
                return end - start
            
    async def postgresql(self, format: str = "ms") -> int | float:
        async with self._bot.pool.acquire() as conn:
            start = time.perf_counter()
            await conn.execute("SELECT 1")
            end = time.perf_counter()

        match format.lower():
            case "ms" | "milliseconds" | "millisecond":
                return (end - start) * 1000
            case _:
                return end - start