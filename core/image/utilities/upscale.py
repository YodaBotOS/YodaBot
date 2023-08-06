from io import BytesIO
from typing import Any

import aiohttp

from core.replicate import Replicate


class Upscaling:
    MODEL_VERSION = "proguy914629bot/real-esrgan:latest"

    def __init__(self, api_token: str, session: aiohttp.ClientSession) -> None:
        self.api_token = api_token
        self.session = session

        self.replicate = Replicate(api_token, session=session)

    async def upscale(self, image: str | bytes, *, scale: int = 2) -> bytes:
        if 1 > scale or scale > 10:
            raise ValueError("Scale must be between 1 and 10")

        prediction = await self.replicate.run(
            self.MODEL_VERSION, img=image, version="General - RealESRGANplus", scale=scale, wait=True
        )
        async with self.session.get(prediction.output) as resp:
            return await resp.read()

    async def __call__(self, image: str | bytes, *, scale: int = 2) -> BytesIO:
        return BytesIO(await self.upscale(image, scale=scale))
