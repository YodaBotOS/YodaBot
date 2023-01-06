import io
from dataclasses import dataclass
from difflib import get_close_matches as find_match_difflib

import aiohttp
from thefuzz.process import extractBests as find_match_fuzzy


@dataclass
class TranslateOCRResult:
    url: str
    original_text: str
    translated_text: str


class TranslateOCR:
    URL = "https://api.yodabot.xyz/v/{}/translate-ocr"
    SCORE_CUTOFF = 50  # For get_language. If the score is lower than this, return None.

    def __init__(self, session: aiohttp.ClientSession, *, api_version="2"):
        self.session: aiohttp.ClientSession = session
        self.api_version = api_version
        self.url = self.URL.format(api_version)

        self.languages = []
        self.languages_all = []

    async def read_img_from_url(self, url: str) -> bytes:
        async with self.session.get(url) as resp:
            img = await resp.read()

        return img

    async def get_languages(self, *, all: bool = False) -> list[dict[str, str]]:
        if self.languages_all and all:
            return self.languages_all
        elif self.languages and not all:
            return self.languages

        async with self.session.get(self.url + "/languages") as resp:
            data = await resp.json()

        raw_languages = data["supportedLanguages"]

        languages = []
        languages_all = []

        for lang in raw_languages:
            if lang["code"] in languages_all or lang["name"] in languages_all:
                continue

            languages_all.append(lang["code"].lower())
            languages_all.append(lang["name"].lower())

            languages.append(lang)

        self.languages = languages
        self.languages_all = languages_all

        if all:
            return self.languages_all
        else:
            return self.languages

    async def get_language(self, lang) -> dict[str, str] | None:
        langs = await self.get_languages()

        for language in langs:
            if lang.lower() in [language["code"].lower(), language["name"].lower()]:
                return language

        return None

    async def search_language(self, query: str, amount: int = 1, *, use_difflib=True):
        langs = await self.get_languages(all=True)

        if use_difflib:
            res = find_match_difflib(query.lower(), langs, amount)
        else:
            res = find_match_fuzzy(query.lower(), langs, score_cutoff=self.SCORE_CUTOFF, limit=amount)

            res = [x[0] for x in res]

        if not res:
            return None

        langs_found = []

        for lang in res:
            d = await self.get_language(lang)

            if d:
                langs_found.append(d)

        return langs_found

    async def call_api(self, img_bytes, lang) -> dict:
        data = aiohttp.FormData()
        data.add_field("image", img_bytes)

        params = {"lang": lang}

        async with self.session.post(self.url + "/render", data=data, params=params) as resp:
            data = await resp.json()

        return data

    async def run(self, img: str | bytes | io.BytesIO, lang: str) -> TranslateOCRResult:
        if lang.lower() not in await self.get_languages(all=True):
            raise ValueError(f"Language {lang} is not supported")

        if isinstance(img, str):
            img = io.BytesIO(await self.read_img_from_url(img))
        elif isinstance(img, bytes):
            img = io.BytesIO(img)

        data = await self.call_api(img, lang)

        passed_data = {
            "url": data["url"],
            "original_text": data["originalText"],
            "translated_text": data["translatedText"],
        }

        return TranslateOCRResult(**passed_data)

    async def __call__(self, img: str | bytes | io.BytesIO, lang: str) -> TranslateOCRResult:
        return await self.run(img, lang)
