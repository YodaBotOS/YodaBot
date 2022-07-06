import discord
from discord.ext.menus import ListPageSource as MenuSource
from utils.paginator import YodaMenuPages


class TranslateLanguagesPaginator(MenuSource):
    async def format_page(self, menu, entries):
        entry = []

        for lang in entries:
            spaces = 6 - len(f'{lang["languageCode"]}')
            entry.append(f'{lang["languageCode"]}{" "*spaces}: {lang["displayName"]}')

        embed = discord.Embed(color=menu.ctx.bot.color)
        embed.title = "Supported Languages:"
        embed.description = '```yml\n' + '\n'.join(entry) + '\n```'

        return embed
