from __future__ import annotations

import json
import os
import typing
from typing import TYPE_CHECKING

import aiohttp
import discord
import regex
from discord import app_commands
from discord.ext import commands

import config
from core.translate import Translate

if TYPE_CHECKING:
    from core.bot import Bot


class AppCommandsTranslator(Translate):
    LOCALES = {
        "american_english": "en",
        "british_english": "en",
        "bulgarian": "bg",
        "chinese": "zh-CN",
        "taiwan_chinese": "zh-TW",
        "croatian": "hr",
        "czech": "cs",
        "danish": "da",
        "dutch": "nl",
        "finnish": "fi",
        "french": "fr",
        "german": "de",
        "greek": "el",
        "hindi": "hi",
        "hungarian": "hu",
        "italian": "it",
        "japanese": "ja",
        "korean": "ko",
        "lithuanian": "lt",
        "norwegian": "no",
        "polish": "pl",
        "brazil_portuguese": "pt",
        "romanian": "ro",
        "russian": "ru",
        "spain_spanish": "es",
        "swedish": "sv",
        "thai": "th",
        "turkish": "tr",
        "ukrainian": "uk",
        "vietnamese": "vi",
    }

    def get_language(self, query: str) -> dict[str, str] | None:
        if code := self.LOCALES.get(query):
            return {"languageCode": code}
        elif query in self.LOCALES.values():
            return {"languageCode": query}


class Translator(app_commands.Translator):
    """
    Translator
    """

    REGEX = regex.compile(r"^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$")

    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot
        self.session: aiohttp.ClientSession = None
        self._translate: Translate = None

    async def load(self):
        self.session = self.bot.session
        self._translate = AppCommandsTranslator(config.PROJECT_ID, session=self.session)

    async def unload(self):
        await self.session.close()

    async def add_to_persistent_cache(self, target: str, message: str, trans: str):
        # if not os.path.exists('data'):
        #     os.mkdir('data')

        # if not os.path.exists('data/translate'):
        #     os.mkdir('data/translate')

        # if not os.path.exists(f'data/translate/translated.json'):
        #     d = {}
        # else:
        #     with open('data/translate/translated.json', 'r') as f:
        #         d = json.load(f)

        # if message not in d:
        #     d[message] = {target: trans}
        # else:
        #     d[message][target] = trans

        # with open('data/translate/translated.json', 'w') as f:
        #     json.dump(d, f, indent=4)

        q = "INSERT INTO translations (target, message, translation) VALUES ($1, $2, $3) ON CONFLICT (message, target) DO UPDATE SET translation = $3;"
        await self.bot.pool.execute(q, target, message, trans)

    async def search_persistent_cache(self, target: str, message: str) -> str | None:
        # if not os.path.exists('data'):
        #     os.mkdir('data')

        # if not os.path.exists('data/translate'):
        #     os.mkdir('data/translate')

        # if not os.path.exists(f'data/translate/translated.json'):
        #     d = {}
        # else:
        #     with open('data/translate/translated.json', 'r') as f:
        #         d = json.load(f)

        # if message in d:
        #     if target in d[message]:
        #         return d[message][target]

        q = "SELECT translation FROM translations WHERE target = $1 AND message = $2;"
        return await self.bot.pool.fetchval(q, target, message)

    def do_check(self, trans, context) -> str | None:
        if context.location in [
            app_commands.TranslationContextLocation.command_name,
            app_commands.TranslationContextLocation.group_name,
        ]:
            trans = trans.replace(" ", "-").lower()
        elif context.location is app_commands.TranslationContextLocation.parameter_name:
            trans = trans.replace(" ", "_").lower()

        if (
            context.location
            in [
                app_commands.TranslationContextLocation.group_description,
                app_commands.TranslationContextLocation.command_description,
                app_commands.TranslationContextLocation.parameter_description,
                app_commands.TranslationContextLocation.other,
            ]
            and len(trans) > 100
        ):
            return None

        if not self.REGEX.fullmatch(trans) and context.location not in [
            app_commands.TranslationContextLocation.group_description,
            app_commands.TranslationContextLocation.command_description,
            app_commands.TranslationContextLocation.parameter_description,
            app_commands.TranslationContextLocation.other,
        ]:
            return None

        return trans

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ) -> str | None:
        message = string.message
        target = locale.name

        if context.location is app_commands.TranslationContextLocation.choice_name:
            return None

        trans = await self.search_persistent_cache(target, message)

        if trans:
            return self.do_check(trans, context)

        try:
            trans = await self._translate.translate(message, target, source_language="en", check_duplicate=True)
        except:
            return None

        res = trans["translated"]

        res2 = self.do_check(res, context)

        res = res2 or res

        await self.add_to_persistent_cache(target, message, res)

        if not res2:
            return None

        return res
