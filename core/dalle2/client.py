import io

import openai

from .enums import *
from .image import *


class GenerateArt:
    def __init__(self, key: str = None):
        if key is not None:
            self.key = key
            openai.api_key = key
        else:
            self.key = openai.api_key

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

    def create_image(self, prompt: str, n: int, *, size: Size, user: str = None) -> GeneratedImages:
        if 1 > n or n > 10:
            raise ValueError("n must be between 1 and 10")

        s = size.get_size()

        response = openai.Image.create(
            prompt=prompt,
            n=n,
            size=s,
            user=user
        )

        return GeneratedImages(self, response)

    def create_image_variations(self, image: str | bytes | io.BytesIO, n: int, *,
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

        return GeneratedImages(self, response)
