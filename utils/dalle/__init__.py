import discord
from discord.ext import commands
from discord.ext.menus import ListPageSource as MenuSource

from core.dalle2 import Image


class DalleImagesPaginator(MenuSource):
    def __init__(self, entries, text, prompt = None):
        super().__init__(entries, per_page=1)

        self.text = text
        self.prompt = prompt

    async def format_page(self, menu, image: Image):
        embed = discord.Embed(color=menu.ctx.bot.color)
        embed.set_image(url=image.url)
        embed.set_author(name=f"Dall·E 2 {(self.text + ' ') if self.text else ''}Result:",
                         icon_url='https://cdn.openai.com/API/images/dalle-icon-1024.png')
        embed.set_footer(text=f'\U000026a0 Warning \U000026a0: All DALL·E images and prompts are logged for security '
                              f'purposes. You will get banned from using DALL·E in this bot if you are using DALL·E '
                              'in a malicious/inappropriate (pretty much anything bad) way.')

        if self.prompt:
            embed.description = self.prompt

        return embed
