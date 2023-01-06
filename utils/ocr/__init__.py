import discord
from discord.ext.menus import ListPageSource as MenuSource

from utils.paginator import YodaMenuPages


class TranslateOCRLanguagesPaginator(MenuSource):
    async def format_page(self, menu: YodaMenuPages, entries: list[dict[str, str]]):
        entry = []

        for lang in entries:
            spaces = 6 - len(f'{lang["code"]}')
            entry.append(f'{lang["code"]}{" "*spaces}: {lang["name"]}')

        embed = discord.Embed(color=menu.ctx.bot.color)
        embed.title = "Supported Languages:"
        embed.description = "```yml\n" + "\n".join(entry) + "\n```"

        return embed
