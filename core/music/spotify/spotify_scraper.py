import aiohttp

from config import *
from core.music.spotify.spotify_client import SpotifyClient


class SpotifyScraper:
    _client = None

    def __init__(
        self, sp_dc=None, sp_key=None, session: aiohttp.ClientSession = None
    ) -> None:
        self._client = SpotifyClient(sp_dc=sp_dc, sp_key=sp_key, session=session)

    async def get(self, url: str) -> dict:
        return await self._client.get(url)

    # def post(self, url: str, payload=None) -> Response:
    #     return self._client.post(url, payload=payload)

    async def get_lyrics(self, track_id: str) -> str | None:
        try:
            return await self.get(
                f"https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}"
            )
        except Exception as ex:
            return None
