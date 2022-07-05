import re
import importlib

import discord
from discord.ext import commands
from discord import app_commands

from utils import converter
from core import ocr

class OCR(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # https://github.com/Rapptz/discord.py/issues/7823#issuecomment-1086830458
        self.ctx_menu = app_commands.ContextMenu(
            name="Image To Text (OCR)",
            callback=self.image_to_text_context_menu
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_load(self):
        importlib.reload(ocr)
        from core.ocr import OCR

        self.bot.ocr = OCR(session=self.bot.session)

    async def cog_unload(self) -> None:
        del self.bot.ocr

        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def ocr(self, image) -> discord.ui.View | discord.Embed:
        text = await self.bot.ocr.request(image)

        if len(text) > 4096:
            url = await self.bot.mystbin.post(text, syntax="text")

            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View on mystb.in", url=url))

            return view

        embed = discord.Embed(color=self.bot.color)
        embed.title = "Image to Text (OCR) Result:"
        embed.description = text

        return embed

    @app_commands.command(name="image-to-text")
    @app_commands.describe(image="The attachment to be converted to text.",
                           url="The URL to an image to be converted to "
                               "text.")
    async def image_to_text(self, interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
        """
        Convert an image to text, known as the phrase OCR (Optical Character Recognition).
        """

        if image is None and url is None:
            return await interaction.response.send_message("Please provide an image or a URL!", ephemeral=True)

        if image and url:
            return await interaction.response.send_message("Please provide only one of image or url!", ephemeral=True)

        if image is not None:
            image = image.url
        else:
            if match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                                     url):
                image = match.group(0)
            else:
                return await interaction.response.send_message("Please provide a valid URL!", ephemeral=True)

        await interaction.response.defer()

        resp = await self.ocr(image)

        if isinstance(resp, discord.ui.View):
            return await interaction.followup.send('Result too long.', view=resp)
        else:
            return await interaction.followup.send(embed=resp)

    @commands.command(name="image-to-text", aliases=["ocr", "itt", "i2t", "image2text", "image-2-text", "imagetotext"])
    async def image_to_text(self, ctx: commands.Context, *, image=None):
        """
        Convert an image to text, known as the phrase OCR (Optical Character Recognition).
        """

        if image is None:
            image = await converter.ImageConverter().convert(ctx, image)
        else:
            image = image.url

        if not image:
            return await ctx.send("Please send a attachment/URL to a image!")

        async with ctx.typing():
            resp = await self.ocr(image)

            if isinstance(resp, discord.ui.View):
                return await ctx.send('Result too long.', view=resp)
            else:
                return await ctx.send(embed=resp)

    async def image_to_text_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        url = None

        if attach := message.attachments:
            url = attach[0].url
        elif embeds := message.embeds:
            for embed in embeds:
                if embed.image:
                    url = embed.image.url
                    break
                elif embed.thumbnail:
                    url = embed.thumbnail.url
                    break
        elif match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                                   message.content):
            url = match.group(0)

        if not url:
            return await interaction.response.send_message("There is no image to convert to text!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        resp = await self.ocr(url)

        if isinstance(resp, discord.ui.View):
            return await interaction.followup.send('Result too long.', view=resp, ephemeral=True)
        else:
            return await interaction.followup.send(embed=resp, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OCR(bot))
