import asyncio
import io
import json
import random
import typing
import uuid

import aiohttp
import yarl


class _Latin1BodyPartReader(aiohttp.multipart.BodyPartReader):
    async def text(self) -> str:
        data = await self.read(decode=True)
        return data.decode("latin1")


class _Latin1MultipartReader(aiohttp.multipart.MultipartReader):
    async def next(self) -> _Latin1BodyPartReader:
        part_reader = await super().next()
        if part_reader is not None:
            part_reader.__class__ = _Latin1BodyPartReader
        return part_reader


FIREFLY_SIZES = typing.Literal[
    "Portrait", "Landscape", "Square", "Widescreen", "Vertical", "Ultrawide", "Ultrawide Portrait"
]

# Hacky way, idc.
class Firefly:
    URL = yarl.URL("https://firefly.adobe.io/spl")
    ASSET_URL = yarl.URL("https://clio-assets.adobe.com/clio-playground")
    SIZES = {  # (Aspect Ratio, Width, Height)
        "Portrait": ((3, 4), 1024, 1408),
        "Landscape": ((4, 3), 1408, 1024),
        "Square": ((1, 1), 1024, 1024),
        "Widescreen": ((16, 9), 1792, 1024),
        "Vertical": ((9, 16), 1024, 1792),
        "Ultrawide": ((21, 9), 2560, 1080),
        "Ultrawide Portrait": ((9, 21), 1080, 2560),
        # "Panoramic": ((32, 9), 3840, 1080),
        # "Panoramic Portrait": ((9, 32), 1080, 3840),
    }

    def __init__(self, token: str, *, session: aiohttp.ClientSession, cdn: tuple):
        self.token = token
        self.session = session

        self.headers = {
            "Origin": "https://firefly.adobe.com",
            "Accept": "multipart/form-data",
            "Authorization": "Bearer " + self.token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "x-api-key": "clio-playground-web",
            "DNT": "1",
        }

        self.s3, self.bucket, self.host = cdn

    @staticmethod
    def generate_settings(
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style_prompt: str = "",
        anchor_prompt: str = "",
        fix_face: bool = True,
        seed: int = None,
    ) -> dict:
        advanced_options = {"style_prompt": style_prompt, "anchor_prompt": anchor_prompt}

        seed = seed or random.randint(0, 100000)
        seed = [{"name": "0", "value": seed, "type": "scalar"}]

        settings = {
            "graph": {"uri": "urn:graph:Text2Image_v3"},
            "params": [
                {"name": "gi_OUTPUT_HEIGHT", "type": "scalar", "value": height},
                {"name": "gi_OUTPUT_WIDTH", "type": "scalar", "value": width},
                {"name": "gt_SEED", "type": "array", "value": seed},
                {
                    "name": "gi_ADVANCED",
                    "type": "string",
                    "value": json.dumps(advanced_options),
                },
                {"name": "gi_USE_FACE_FIX", "type": "boolean", "value": fix_face},
            ],
            "inputs": {
                "gt_PROMPT": {
                    "id": str(uuid.uuid4()),
                    "toStore": {"lifeCycle": "session"},
                    "type": "string",
                    "value": prompt,
                }
            },
            "outputs": {
                "gt_GEN_IMAGE": {
                    "id": str(uuid.uuid4()),
                    "type": "array",
                    "expectedMimeType": "image/jpeg",
                    "expectedArrayLength": 1,
                },
                "gt_GEN_STATUS": {
                    "id": str(uuid.uuid4()),
                    "type": "array",
                },
            },
        }

        return settings

    async def get_image_styles(self) -> dict:
        url = Firefly.ASSET_URL / "image-styles" / "v4" / "en-US" / "content.json"
        async with self.session.get(url) as resp:
            return await resp.json()

    async def text_to_image(
        self,
        prompt: str,
        amount: int,
        *,
        width: int = 1024,
        height: int = 1024,
        styles: list[str] = [],
        fix_face: bool = True,
        seed: int = None,
    ) -> list[str]:
        styles = styles or []
        _styles = await self.get_image_styles()
        style_prompt = []
        anchor_prompt = []
        leftover_styles = styles.copy()
        for s in _styles["styles"]:
            for style in styles:
                if style.lower() == s["title"].lower():
                    if s["style_prompt"]:
                        style_prompt.append(s["style_prompt"])
                    if s["anchor_prompt"]:
                        anchor_prompt.append(s["anchor_prompt"])
                    leftover_styles.remove(style)

        if leftover_styles:
            raise ValueError(f"Invalid styles: {', '.join(leftover_styles)}")

        for i in _styles["styles"]:
            if i["title"].lower() in prompt:
                prompt = prompt.replace(i["title"].lower(), "")
                if i["style_prompt"]:
                    style_prompt.append(i["style_prompt"])
                if i["anchor_prompt"]:
                    anchor_prompt.append(i["anchor_prompt"])

        style_prompt = ", ".join(style_prompt)
        anchor_prompt = ", ".join(anchor_prompt)

        settings = self.generate_settings(prompt, width, height, style_prompt, anchor_prompt, fix_face, seed)

        images = await asyncio.gather(*[self._text_to_image_inner_task(settings) for _ in range(amount)])
        return [self.post_to_cdn(i, folder="firefly/text-to-image") for i in images]

    async def _text_to_image_inner_task(self, settings: dict):
        h = self.headers.copy()
        h["x-session-id"] = str(uuid.uuid4())
        h["x-request-id"] = str(uuid.uuid4())

        boundary = str(uuid.uuid4().hex)
        boundary = "----WebKitFormBoundary" + boundary

        h["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        settings["params"][2]["value"][0]["value"] = random.randint(0, 100000)

        with aiohttp.MultipartWriter("form-data", boundary=boundary) as writer:
            data = json.dumps(settings)
            part = writer.append(data, {"Content-Type": "application/json"})
            part.set_content_disposition("form-data", name="request", filename="blob")

            async with self.session.post(self.URL, headers=h, data=writer) as resp:
                reader = _Latin1MultipartReader(resp.headers, resp.content)
                image = None
                while True:
                    part = await reader.next()
                    if part.headers[aiohttp.hdrs.CONTENT_TYPE] == "image/jpeg":
                        image = await part.read(decode=False)
                    if image:
                        break

                return io.BytesIO(image)

    def post_to_cdn(self, image: io.BytesIO, *, folder: str) -> str:
        key = folder + "/" + str(uuid.uuid4()) + ".jpg"
        url = self.host / key

        self.cdn.upload_fileobj(
            image,
            Bucket=self.bucket,
            Key=key,
        )

        return url
