from urllib.parse import quote_plus

import aiohttp
import yarl


class SerpAPI:
    URL = yarl.URL("https://api.tavily.com/")

    def __init__(self, api_key: str, *, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session

    async def google_search(self, query: str) -> dict:
        params = {
            "query": query,
            "api_key": self.api_key,
            "search_depth": "advanced",
            "include_answer": "true",
            "max_results": 20,
        }

        async with self.session.get(self.URL / "search", params=params) as resp:
            return await resp.json()
