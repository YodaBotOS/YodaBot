import json
from difflib import get_close_matches as find_one_difflib

import aiohttp
from thefuzz.process import extractOne as find_one_fuzzy

from core.auth import get_gcp_token


class Translate:
    PARENT = "projects/{project_id}"
    URL = "https://translation.googleapis.com/v3/{parent}"
    SCORE_CUTOFF = 50 # For search_language. If the score is lower than this, return None.

    def __init__(self, project_id: str, *, session: aiohttp.ClientSession):
        self.session = session
        self.project_id = project_id
        self.parent = self.PARENT.format(project_id=project_id)
        self.url = self.URL.format(parent=self.parent)
        self.languages = None

        self.language_aliases = {
            'Chinese': 'zh-CN',
            'Mandarin': 'zh-CN',
            'eng': 'en',
        }

    async def get_languages(self, *, force_call=False, add_to_cache=True) -> list[dict[str, str | bool]]:
        if not force_call and self.languages:
            return self.languages

        key = get_gcp_token(from_gcloud=True)

        params = {'displayLanguageCode': 'en'}
        headers = {'Authorization': f'Bearer {key}'}

        async with self.session.get(self.url + '/supportedLanguages', params=params, headers=headers) as resp:
            resp.raise_for_status()

            js = await resp.json()

            if add_to_cache:
                self.languages = js['languages']

            self.build_language_aliases()

            return self.languages

    def build_language_aliases(self) -> dict[str, str | int | float]:
        if not self.languages:
            raise Exception("Languages not loaded")

        for lang_data in self.languages.copy():
            for alias, lang in self.language_aliases.items():
                if lang in [lang_data['languageCode'], lang_data['displayName']]: # Better than if x == lang or y == lang
                    lang_data_alias = lang_data.copy()
                    lang_data_alias['displayName'] = alias
                    self.languages.append(lang_data_alias)

        return self.languages

    def search_language(self, query: str, *, use_difflib=True) -> dict[str, str | int | float] | None:
        if not self.languages:
            raise Exception("Languages not loaded")

        lang_names = []

        for lang_data in self.languages:
            lang_names.append(lang_data['displayName'].lower())
            lang_names.append(lang_data['languageCode'].lower())

        # print(lang_names)

        if use_difflib:
            res = find_one_difflib(query.lower(), lang_names)[0]
        else:
            res = find_one_fuzzy(query.lower(), lang_names, score_cutoff=self.SCORE_CUTOFF)[0]

        if not res:
            return None

        for lang_data in self.languages:
            if res in [lang_data['languageCode'].lower(), lang_data['displayName'].lower()]:  # Better than if x == lang or y == lang
                return lang_data

    async def detect_language(self, text: str, *, raw=False) -> dict[str, str | int | float] | None:
        key = get_gcp_token(from_gcloud=True)

        headers = {'Authorization': f'Bearer {key}'}

        data = {
            "content": text,
        }

        data = json.dumps(data)

        async with self.session.post(self.url + ':detectLanguage', data=data, headers=headers) as resp:
            resp.raise_for_status()

            js = await resp.json()

            if raw:
                return js

            # Find the data with the most confidence, then return that data
            detected = js['languages']

            if not detected:
                return None

            result = sorted(detected, key=lambda x: x['confidence'], reverse=True)[0]

            return result

    async def translate(self, text: str, target_language: str, *, source_language: str = None,
                        mime_type: str = "text/plain") -> dict:
        # Make target and source language params to use language code instead of display name

        target_language = self.search_language(target_language)

        if not target_language:
            raise Exception("Target language not found")

        target_language = target_language['languageCode']

        if source_language:
            source_language = self.search_language(source_language)

            if not source_language:
                raise Exception("Source language not found")

            source_language = source_language['languageCode']

        key = get_gcp_token(from_gcloud=True)

        headers = {'Authorization': f'Bearer {key}'}

        data = {
            "targetLanguageCode": target_language,
            "contents": [text],
            "mimeType": mime_type
        }

        if source_language:
            data["sourceLanguageCode"] = source_language

        data = json.dumps(data)

        async with self.session.post(self.url + ':translateText', data=data, headers=headers) as resp:
            resp.raise_for_status()

            js = await resp.json()

            result = {'translated': js['translations'][0]['translatedText']}

            if lang := js['detectedLanguageCode']:
                result['sourceLanguageCode'] = lang
            else:
                result['sourceLanguageCode'] = source_language
