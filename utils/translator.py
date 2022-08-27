import typing

import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

import config
from core.translate import Translate


class Translator(app_commands.Translator):
    """
    Translator
    """

    def __init__(self, bot: commands.Bot):
        super().__init__()

        self.bot = bot
        self.session: aiohttp.ClientSession = None
        self.translate: Translate = None

    async def load(self):
        session = aiohttp.ClientSession()
        self.translate = Translate(config.PROJECT_ID, session=session)
        await self.translate.get_languages(force_call=True, add_to_cache=True)

    async def unload(self):
        await self.session.close()

    async def translate(self, string: app_commands.locale_str, locale: discord.Locale,
                        context: app_commands.TranslationContext) -> typing.Optional[str]:
        message = string.message
        target = locale.value  # type: ignore

        try:
            trans = await self.translate.translate(message, target)
        except:
            return None

        return trans['translated']
