from urllib.parse import quote_plus

import aiohttp
import yarl


class SerpAPI:
    URL = yarl.URL("https://api.tavily.com/")

    def __init__(self, api_key: str, *, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session

    async def google_search(self, query: str) -> dict:
        body = {
            "query": query,
            "api_key": self.api_key,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 3,
        }

        async with self.session.post(self.URL / "search", json=body) as resp:
            return await resp.json()
