import asyncio
import io
from dataclasses import dataclass, field
from urllib.parse import quote

import aiohttp
import spotipy2.types
from discord.app_commands import Choice
from spotipy2 import Spotify
from spotipy2.auth import ClientCredentialsFlow

from core.music.spotify.spotify_scraper import SpotifyScraper


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
    id: str = None

    def __str__(self):
        return f"{self.title} - {', '.join(self.artists)}"


class LyricLocalAPI:
    def __init__(
        self, session: aiohttp.ClientSession, cdn: tuple, client_id: str, client_secret: str, sp_dc: str, sp_key: str
    ):
        self.session = session
        self.cdn, self.bucket, self.host = cdn
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp_dc = sp_dc
        self.sp_key = sp_key

        self._client = SpotifyScraper(sp_dc=sp_dc, sp_key=sp_key, session=session)
        self.spotify = Spotify(ClientCredentialsFlow(client_id, client_secret))

    async def get_lyrics(self, track_id_or_query: str, *, raw: bool = False) -> dict | None:
        try:
            track = await self.get_track_info(track_id_or_query)
        except:
            track = await self.search_autocomplete(track_id_or_query, limit=1)
            track = track[0]
            track = await self.get_track_info(track["id"])

        lyrics = await self._client.get_lyrics(track.id)
        if lyrics is None:
            return LyricResult.empty()

        if raw:
            return lyrics

        lyrics = "\n".join([x["words"] for x in lyrics["lyrics"]["lines"]])
        title = track.name
        artist = ", ".join([a.name for a in track.artists])
        images = {
            "track": await self._post_to_cdn(
                track.album.images[0]["url"],
                f'lyrics/{title.replace(" ", "_")}-{" ".join([a.name.replace(" ", "_") for a in track.artists])}/track.jpg',
            ),
            "background": await self._post_to_cdn(
                track.album.images[1]["url"],
                f'lyrics/{title.replace(" ", "_")}-{" ".join([a.name.replace(" ", "_") for a in track.artists])}/track.jpg',
            ),
        }

        return {"title": title, "artist": artist, "lyrics": lyrics, "images": images}

    async def search_autocomplete(self, query: str, limit: int = 10) -> list[dict]:
        x = await self.spotify.search(query, types=[spotipy2.types.Track], limit=limit)
        items = x["tracks"].items
        return [{"title": i.name, "artists": [a.name for a in i.artists], "id": i.id} for i in items]

    async def get_track_info(self, track_id: str):
        x = await self.spotify.get_track(track_id)
        return x

    async def _post_to_cdn(self, url: str, key: str):
        async with self.session.get(url) as resp:
            data = await resp.read()

        self.cdn.upload_fileobj(
            io.BytesIO(data),
            Bucket=self.bucket,
            Key=key,
        )

        url = f"{self.host}/{quote(key, safe='')}"
        return url


class Lyrics:
    local = LyricLocalAPI
    CACHE = {}
    URL = "https://api.yodabot.xyz/v/{}/lyrics"  # Use Yoda API

    def __init__(
        self,
        local: LyricLocalAPI,
        *,
        loop: asyncio.AbstractEventLoop = None,
        session: aiohttp.ClientSession = None,
        api_version="latest",
    ):
        self.session: aiohttp.ClientSession = session or aiohttp.ClientSession()

        self.url = self.URL.format(api_version)  # Yoda API latest

        self.loop = loop or asyncio.get_event_loop()

        self.CACHE_TTL_TASKS = []

        self._local = local

    async def __call__(self, query: str, *, cache: bool = True, get_from_cache: bool | None = None):
        return self.search(query, cache=cache, get_from_cache=get_from_cache)

    def set_cache(self, key, value, ttl=24*60*60):
        self.CACHE[key] = value

        async def task():
            while True:
                await asyncio.sleep(ttl)
                self.CACHE.pop(key)

        if ttl is not None:
            self.CACHE_TTL_TASKS.append(self.loop.create_task(task()))

    def get_cache(self, key):
        return self.CACHE.get(key)

    async def call_api(self, query_or_id: str) -> dict:
        try:
            if self._local:
                d = await self._local.get_lyrics(query_or_id)
                if d and d["lyrics"]:
                    return d
        except:
            pass

        return dict()

        params = {"q": query_or_id}

        async with self.session.get(self.url + "/search", params=params) as resp:
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

        try:
            if self._local:
                d = await self._local.search_autocomplete(query, limit=amount)
                if d:
                    suggestions = [LyricAutocompleteSuggestions(**suggestion) for suggestion in d][:amount]

                    if slash_autocomplete:
                        return [Choice(name=str(suggestion), value=str(suggestion.id)) for suggestion in suggestions]

                    return suggestions
        except:
            pass

        params = {"q": query, "amount": amount}

        async with self.session.get(self.url + "/suggest", params=params) as resp:
            d = await resp.json()

        suggestions = [LyricAutocompleteSuggestions(**suggestion) for suggestion in d][:amount]

        if slash_autocomplete:
            return [Choice(name=str(suggestion), value=str(suggestion)) for suggestion in suggestions]

        return suggestions
