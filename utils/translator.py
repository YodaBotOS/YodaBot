import os
import typing
import json
import asyncio

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import config
from core.translate import Translate


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
        "vietnamese": "vi"
    }
    
    def get_language(self, query: str) -> dict[str, str] | None:
        print(query)
        if code := self.LOCALES.get(query):
            return {'languageCode': code}
        elif query in self.LOCALES.values():
            return {'languageCode': query}


class Translator(app_commands.Translator):
    """
    Translator
    """

    def __init__(self, bot: commands.Bot):
        super().__init__()

        self.bot = bot
        self.session: aiohttp.ClientSession = None
        self._translate: Translate = None
        self.sem = asyncio.Semaphore(1)

    async def load(self):
        self.session = self.bot.session
        self._translate = AppCommandsTranslator(config.PROJECT_ID, session=self.session)

    async def unload(self):
        await self.session.close()
    
    async def add_to_persistent_cache(self, target: str, message: str, trans: str):
        async with self.sem:
            if not os.path.exists('data'):
                os.mkdir('data')
                
            if not os.path.exists('data/translate'):
                os.mkdir('data/translate')
                
            if not os.path.exists(f'data/translate/translated.json'):
                d = {}
            else:
                with open('data/translate/translated.json', 'r') as f:
                    d = json.load(f)
                    
            if message not in d:
                d[message] = {target: trans}
            else:
                d[message][target] = trans
                
            with open('data/translate/translated.json', 'w') as f:
                json.dump(d, f, indent=4)
    
    async def search_persistent_cache(self, target: str, message: str) -> str | None:
        async with self.sem:
            if not os.path.exists('data'):
                os.mkdir('data')
                
            if not os.path.exists('data/translate'):
                os.mkdir('data/translate')
                
            if not os.path.exists(f'data/translate/translated.json'):
                d = {}
            else:
                with open('data/translate/translated.json', 'r') as f:
                    d = json.load(f)
                    
            if message in d:
                if target in d[message]:
                    return d[message][target]

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ) -> typing.Optional[str]:
        message = string.message
        target = locale.name
        
        if context.location is app_commands.TranslationContextLocation.choice_name:
            return None
        
        trans = await self.search_persistent_cache(target, message)
        
        if trans:
            return trans

        try:
            trans = await self._translate.translate(message, target, source_language='en', check_duplicate=True)
        except:
            return None
        
        res = trans["translated"]
        
        if context.location in [app_commands.TranslationContextLocation.command_name, app_commands.TranslationContextLocation.group_name]:
            res = res.replace(' ', '-')
        elif context.location is app_commands.TranslationContextLocation.parameter_name:
            res = res.replace(' ', '_')
        
        await self.add_to_persistent_cache(target, message, res)

        return res
