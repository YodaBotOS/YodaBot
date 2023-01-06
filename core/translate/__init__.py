import json
from difflib import get_close_matches as find_one_difflib
from urllib.parse import quote_plus as url_param_endcode

import aiohttp
from thefuzz.process import extractOne as find_one_fuzzy

from core.auth import get_gcp_token


class Translate:
    PARENT = "projects/{project_id}"
    URL = "https://translation.googleapis.com/v3/{parent}"
    SCORE_CUTOFF = 50  # For get_language. If the score is lower than this, return None.
    INPUT_TOOLS_URI = (
        "https://inputtools.google.com/request"  # ?text={text}&itc={language_code}-t-i0-und&num={num_choices}
    )
    INPUT_TOOLS_ITC = {
        "zh-CN": "zh-t-i0-pinyin",
        "zh-TW": "zh-t-i0-pinyin",
        "zh": "zh-t-i0-pinyin",
    }

    def __init__(self, project_id: str, *, session: aiohttp.ClientSession):
        self.session = session
        self.project_id = project_id
        self.parent = self.PARENT.format(project_id=project_id)
        self.url = self.URL.format(parent=self.parent)
        self.languages = []
        self.raw_languages = []

        self.language_aliases = {
            "Chinese": "zh-CN",
            "Mandarin": "zh-CN",
            # 'eng': 'en',
            "en-US": "en",
            "en-GB": "en",
            "pt-BR": "pt",
            "es-ES": "es",
            "sv-SE": "sv",
        }

    async def get_languages(self, *, force_call=False, add_to_cache=True) -> list[dict[str, str | bool]]:
        if not force_call and self.languages:
            return self.languages

        key = get_gcp_token(from_gcloud=True)

        params = {"displayLanguageCode": "en"}
        headers = {"Authorization": f"Bearer {key}"}

        async with self.session.get(self.url + "/supportedLanguages", params=params, headers=headers) as resp:
            resp.raise_for_status()

            js = await resp.json()

            if add_to_cache:
                self.languages = js["languages"]

            self.raw_languages = self.languages.copy()

            self.build_language_aliases()

            return self.languages

    def build_language_aliases(self) -> list[dict[str, str | int | float]]:
        if not self.languages:
            raise Exception("Languages not loaded")

        for lang_data in self.languages.copy():
            for alias, lang in self.language_aliases.items():
                if lang in [
                    lang_data["languageCode"],
                    lang_data["displayName"],
                ]:  # Better than if x == lang or y == lang
                    lang_data_alias = lang_data.copy()
                    lang_data_alias["displayName"] = alias
                    self.languages.append(lang_data_alias)

        return self.languages

    def get_language(self, query: str, *, use_difflib=True) -> dict[str, str | int | float] | None:
        if not self.languages:
            raise Exception("Languages not loaded")

        lang_names = self.get_all_languages(lowered=True)

        # print(lang_names)

        if use_difflib:
            res = find_one_difflib(query.lower(), lang_names)
        else:
            res = find_one_fuzzy(query.lower(), lang_names, score_cutoff=self.SCORE_CUTOFF)

        if not res:
            return None

        res = res[0]

        for lang_data in self.languages:
            if res in [
                lang_data["languageCode"].lower(),
                lang_data["displayName"].lower(),
            ]:  # Better than if x == lang or y == lang
                return lang_data

    def get_all_languages(self, *, lowered=False, only=None):
        langs = []

        for lang_data in self.languages:
            if only:
                if only == "displayName":
                    langs.append(lang_data["displayName"].lower() if lowered else lang_data["displayName"])
                elif only == "languageCode":
                    langs.append(lang_data["languageCode"].lower() if lowered else lang_data["languageCode"])
            else:
                langs.append(lang_data["displayName"].lower() if lowered else lang_data["displayName"])
                langs.append(lang_data["languageCode"].lower() if lowered else lang_data["displayName"])

        return langs

    async def detect_language(self, text: str, *, raw=False) -> dict[str, str | int | float] | None:
        key = get_gcp_token(from_gcloud=True)

        headers = {"Authorization": f"Bearer {key}"}

        data = {
            "content": text,
        }

        data = json.dumps(data)

        async with self.session.post(self.url + ":detectLanguage", data=data, headers=headers) as resp:
            resp.raise_for_status()

            js = await resp.json()

            if raw:
                return js

            # Find the data with the most confidence, then return that data
            detected = js["languages"]

            if not detected:
                return None

            result = sorted(detected, key=lambda x: x["confidence"], reverse=True)[0]

            return result

    async def input_tools(
        self, text: str, language: str, *, num_choices: int = 1, raw=False
    ) -> dict[str, str | int | float | list[str]]:
        # This method is just to explicitly use the language's keyboard (instead of ASCII text).

        lang = self.get_language(language)["languageCode"]

        if lang in self.INPUT_TOOLS_ITC:
            itc = self.INPUT_TOOLS_ITC[lang]
        else:
            itc = f"{lang}-t-i0-und"

        url = self.INPUT_TOOLS_URI

        params = {
            "text": text,
            "itc": itc,
            "num": num_choices,
        }

        for p_name, p_value in params.items():
            p_value = str(p_value)

            p_name_final = f"&{p_name}="
            if url == self.INPUT_TOOLS_URI:
                p_name_final = f"?{p_name}="

            url += p_name_final + url_param_endcode(p_value).replace("+", "%20")

        async with self.session.get(url) as resp:
            content = (await resp.read()).decode()
            data = json.loads(content)

            if raw:
                return data

            try:
                if not (choices := data[1][0][1]):
                    choices = [text]
            except:
                choices = [text]

            result = {
                "source": text,
                "sourceLanguageCode": lang,
                "numChoices": num_choices,
                "choices": choices,
                "itc": itc,
            }

            return result

    async def translate(
        self,
        text: str,
        target_language: str,
        *,
        source_language: str = None,
        mime_type: str = "text/plain",
        raw=False,
    ) -> dict:
        # Make target and source language params to use language code instead of display name

        target_language = self.get_language(target_language)

        if not target_language:
            raise Exception("Target language not found")

        target_language = target_language["languageCode"]

        if source_language:
            source_language = self.get_language(source_language)

            if not source_language:
                raise Exception("Source language not found")

            source_language = source_language["languageCode"]
        else:
            source_language = (await self.detect_language(text))["languageCode"]

        text = (await self.input_tools(text, source_language))["choices"][0]

        key = get_gcp_token(from_gcloud=True)

        headers = {"Authorization": f"Bearer {key}"}

        data = {
            "targetLanguageCode": target_language,
            "contents": [text],
            "mimeType": mime_type,
        }

        if source_language:
            data["sourceLanguageCode"] = source_language

        data = json.dumps(data)

        async with self.session.post(self.url + ":translateText", data=data, headers=headers) as resp:
            resp.raise_for_status()

            js = await resp.json()

            if raw:
                return js

            result = {"translated": js["translations"][0]["translatedText"]}

            if lang := js["translations"][0].get("detectedLanguageCode"):
                result["sourceLanguageCode"] = lang
            else:
                result["sourceLanguageCode"] = source_language

            return result
