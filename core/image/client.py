import io
import uuid

import openai
import aiohttp

from .enums import *
from .image import *
from .style import *
from .dataclass import AnalyzeResult


class ImageUtilities:
    def __init__(self, s3, session: aiohttp.ClientSession, keys: tuple[str]):
        self.openai_key = keys[0]
        openai.api_key = keys[0]
        self.dream_key = keys[1]

        self.s3, self.bucket, self.host = s3
        self.session = session

    @property
    def style(self):
        return GenerateStyleArt((self.s3, self.bucket, self.host), self.session, self.dream_key)

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }

    async def _upload_to_cdn(self, gen: GeneratedImages):
        # Read the url in gen.images[].url and upload it to boto3 S3 client.

        counter = 1
        img_id = uuid.uuid4()

        for image in gen.images:
            original_url = image.url

            async with self.session.get(original_url) as resp:
                data = await resp.read()

            # Upload to S3
            self.s3.upload_fileobj(
                io.BytesIO(data),
                Bucket=self.bucket,
                Key=f"dalle2-results/{img_id}/{counter}.png"
            )

            image.url = f"{self.host}/dalle2-results/{img_id}/{counter}.png"

            counter += 1

    async def create_image(self, prompt: str, n: int, *, size: Size, user: str = None) -> GeneratedImages:
        if 1 > n or n > 10:
            raise ValueError("n must be between 1 and 10")

        s = size.get_size()

        response = openai.Image.create(
            prompt=prompt,
            n=n,
            size=s,
            user=user
        )

        gen = GeneratedImages(self, response)
        await self._upload_to_cdn(gen)

        return gen

    async def create_image_variations(self, image: str | bytes | io.BytesIO, n: int, *,
                                      size: Size, user: str = None) -> GeneratedImages:
        if 1 > n or n > 10:
            raise ValueError("n must be between 1 and 10")

        s = size.get_size()

        if isinstance(image, str):
            image = open(image, "rb").read()
        elif isinstance(image, io.BytesIO):
            image = image.getvalue()

        response = openai.Image.create_variation(
            image=image,
            n=n,
            size=s,
            user=user
        )

        gen = GeneratedImages(self, response)
        await self._upload_to_cdn(gen)

        return gen

    async def analyze(self, image: str | bytes | io.BytesIO) -> AnalyzeResult:
        if isinstance(image, str):
            image = open(image, "rb").read()
        elif isinstance(image, io.BytesIO):
            image = image.getvalue()

        data = aiohttp.FormData()
        data.add_field("image", image)

        async with self.session.post("https://api.yodabot.xyz/api/image/analyze", data=data) as resp:
            js = await resp.json()

        return AnalyzeResult(js)
