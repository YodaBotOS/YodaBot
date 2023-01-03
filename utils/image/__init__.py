import discord
from discord.ext import commands
from discord.ext.menus import ListPageSource as MenuSource

from core.dalle2 import Image
from core.dalle2.style import GeneratedImage


class DalleImagesPaginator(MenuSource):
    def __init__(self, entries, text, prompt=None):
        super().__init__(entries, per_page=1)

        self.text = text
        self.prompt = prompt

    async def format_page(self, menu, image: Image):
        embed = discord.Embed(color=menu.ctx.bot.color)
        embed.set_image(url=image.url)
        embed.set_author(name=f"{(self.text + ' ') if self.text else ''}Result:",
                         icon_url=menu.ctx.author.display_avatar.url)
        embed.set_footer(text=f'All images and prompts are logged for security purposes. You will get banned from '
                              f'using this feature in this bot if you are using it in a malicious/inappropriate '
                              '(pretty much anything bad) way.')

        if self.prompt:
            embed.description = self.prompt

        return embed


class DalleArtPaginator(MenuSource):
    def __init__(self, entries, prompt=None):
        super().__init__(entries, per_page=1)

        self.prompt = prompt

    async def format_page(self, menu, image: GeneratedImage):
        embed = discord.Embed(color=menu.ctx.bot.color)
        embed.set_image(url=image.result)
        embed.set_author(name=f"Image Generation (Style) Result:",
                         icon_url=menu.ctx.author.display_avatar.url)
        embed.set_footer(text=f'All images and prompts are logged for security purposes. You will get banned from '
                              f'using this feature in this bot if you are using it in a malicious/inappropriate '
                              '(pretty much anything bad) way.')

        if self.prompt:
            embed.description = self.prompt

        return embed
