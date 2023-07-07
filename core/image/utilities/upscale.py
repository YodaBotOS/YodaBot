from io import BytesIO
from typing import Any

import aiohttp

from core.replicate import Replicate


class Upscaling:
    MODEL_VERSION = "proguy914629bot/real-esrgan:858b0322654132dfecbebda42796a03169b66092d3e3479fc7811d5847799ab7"

    def __init__(self, api_token: str, session: aiohttp.ClientSession) -> None:
        self.api_token = api_token
        self.session = session

        self.replicate = Replicate(api_token, session=session)

    async def upscale(self, image: str | bytes) -> bytes:
        prediction = await self.replicate.run(self.MODEL_VERSION, image=image, wait=True)
        async with self.session.get(prediction.output[0]) as resp:
            return await resp.read()

    async def __call__(self, image: str | bytes) -> BytesIO:
        return BytesIO(await self.upscale(image))
