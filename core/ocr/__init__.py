import re
import json
import base64

import aiohttp
from core.auth import get_gcp_token


class OCR:
    URL = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self, *, session: aiohttp.ClientSession):
        self.session = session

    async def read_url(self, url: str) -> bytes:
        async with self.session.get(url) as resp:
            return await resp.read()

    async def request(self, data: str | bytes, *, raw=False) -> str | dict:
        if isinstance(data, str):
            if re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", data):
                data = await self.read_url(data)
            else:
                raise TypeError("Invalid data")

        key = get_gcp_token()

        headers = {"Content-Type": "application/json", "Accept-Charset": "UTF-8"}

        params = {"key": key}

        data = {
            "requests": [
                {
                    "image": {
                        "content": base64.b64encode(data).decode("utf-8"),
                    },
                    "features": [
                        {
                            "type": "TEXT_DETECTION",
                        }
                    ]
                }
            ]
        }

        data = json.dumps(data)

        async with self.session.post(self.URL, headers=headers, data=data, params=params) as resp:
            resp.raise_for_status()  # Check status

            js = await resp.json()

            if raw:
                return js

            response = js["responses"][0]

            return response["fullTextAnnotation"]["text"]
