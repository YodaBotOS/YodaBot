import aiohttp
import yarl
from urllib.parse import quote_plus


class SerpAPI:
    URL = yarl.URL("https://seo-api.p.rapidapi.com/v1/")

    def __init__(self, api_key: str, *, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session

    async def google_search(
        self, query: str, *, location: str = "US"
    ) -> dict:  # Purpose of location is just for language
        # params = {
        #     "q": query,
        # }

        headers = {
            "X-User-Agent": "desktop",
            "X-RapidAPI-Key": self.api_key,
        }

        if location:
            headers["X-Proxy-Location"] = location

        async with self.session.get(self.URL / f"search/q={quote_plus(query)}", headers=headers) as resp:
            return await resp.json()
