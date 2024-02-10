import asyncio
import io
import math
import typing

import aiohttp

from core.replicate import Replicate, ReplicateResult

WH = typing.Literal[128, 256, 512, 768, 1024]


class Midjourney:
    MODEL_VERSION = "prompthero/openjourney:latest"

    def __init__(
        self, api_token: str, *, session: aiohttp.ClientSession, cdn: tuple
    ) -> None:
        self.replicate = Replicate(api_token, session=session)
        self.session = session
        self.cdn, self.bucket, self.host = cdn

    def check(self, n: int, width: WH, height: WH):
        if width not in [128, 256, 512, 768, 1024] or height not in [
            128,
            256,
            512,
            768,
            1024,
        ]:
            raise ValueError(
                "width and height must be one of 128, 256, 512, 768, 1024."
            )
        elif width >= 1024 and height >= 1024:
            raise ValueError("width and height must be less than 1024.")
        elif width + height > (1024 + 768):
            raise ValueError(
                "width and height must be max 1024x768 or 768x1024 - memory limits."
            )

        if n > 10:
            raise ValueError("amount of pictures to be generated must be <=10.")

    async def generate(
        self, prompt: str, n: int, *, width: WH, height: WH, publish: bool = True
    ) -> ReplicateResult:
        self.check(n, width, height)

        prompt = "mdjrny-v4 style " + prompt

        result = None

        if width + height == (1024 + 768) and n > 1:
            # memory limits, hacky workaround:
            # amount = 1, do manually until n is achieved
            base = await self.replicate.run(
                self.MODEL_VERSION, wait=True, prompt=prompt, width=width, height=height
            )
            imgs = []
            for i in range(n - 1):
                imgs.append(
                    await self.replicate.run(
                        self.MODEL_VERSION,
                        wait=True,
                        prompt=prompt,
                        width=width,
                        height=height,
                    )
                )

            base.output.extend([i.output[0] for i in imgs])

            result = base
        elif n == 1:
            result = await self.replicate.run(
                self.MODEL_VERSION, wait=True, prompt=prompt, width=width, height=height
            )
        else:
            base = await self.replicate.run(
                self.MODEL_VERSION, wait=True, prompt=prompt, width=width, height=height
            )
            _imgs = []
            _tasks = []
            for i in range(math.ceil((n - 1) / 4)):
                _tasks.append(
                    self.replicate.run(
                        self.MODEL_VERSION,
                        wait=True,
                        prompt=prompt,
                        width=width,
                        height=height,
                        num_outputs=4,
                    )
                )

            _imgs = await asyncio.gather(*_tasks)

            imgs = []
            for i in _imgs:
                imgs.extend(i.output)

            base.output.extend(imgs)
            result = base

        if publish:
            for i, furl in enumerate(result.output):
                key = f"midjourney-images/{result.id}/{i}.png"

                async with self.session.get(furl) as resp:
                    data = await resp.read()

                self.cdn.upload_fileobj(
                    io.BytesIO(data),
                    Bucket=self.bucket,
                    Key=key,
                )

                url = f"{self.host}/{key}"

                result.output[i] = url

        return result
