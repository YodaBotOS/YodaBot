import re
import importlib

import discord
from discord.ext import commands
from discord import app_commands

from core import ocr, trocr
from utils import converter
from utils.ocr import TranslateOCRLanguagesPaginator, YodaMenuPages


class OCR(commands.Cog):
    """
    OCR (Optical Character Recognition)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ocr: ocr.OCR = None
        self.trocr: trocr.TranslateOCR = None

        # https://github.com/Rapptz/discord.py/issues/7823#issuecomment-1086830458
        self.ctx_menu_ocr = app_commands.ContextMenu(
            name="Image To Text (OCR)",
            callback=self.image_to_text_context_menu
        )
        self.bot.tree.add_command(self.ctx_menu_ocr)

        self.ctx_menu_trocr = app_commands.ContextMenu(
            name="Translate Image (Translate OCR)",
            callback=self.trocr_context_menu
        )
        self.bot.tree.add_command(self.ctx_menu_trocr)

    async def cog_load(self):
        importlib.reload(ocr)
        importlib.reload(trocr)
        from core.ocr import OCR
        from core.trocr import TranslateOCR

        self.bot.ocr = OCR(session=self.bot.session)
        self.bot.trocr = TranslateOCR(session=self.bot.session)

        self.ocr = self.bot.ocr
        self.trocr = self.bot.trocr

    async def cog_unload(self) -> None:
        del self.bot.ocr
        del self.bot.trocr

        self.bot.tree.remove_command(self.ctx_menu_ocr.name, type=self.ctx_menu_ocr.type)
        self.bot.tree.remove_command(self.ctx_menu_trocr.name, type=self.ctx_menu_trocr.type)

    async def ocr_image(self, image) -> discord.ui.View | discord.Embed:
        text = await self.ocr.request(image)

        if len(text) > 4096:
            url = await self.bot.mystbin.create_paste("result.txt", text, syntax="txt")

            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View on mystb.in", url=url))

            return view

        embed = discord.Embed(color=self.bot.color)
        embed.title = "Image to Text (OCR) Result:"
        embed.description = text

        return embed

    async def translate_ocr(self, image, lang: str, *, with_original_text: bool = True) -> discord.Embed:
        res = await self.trocr.run(image, lang)

        embed = discord.Embed(color=self.bot.color)

        embed.title = "Translated OCR Result:"

        embed.description = ""

        if with_original_text:
            if len(res.original_text) > 2000:
                url = await self.bot.mystbin.create_paste("original-text.txt", res.original_text, syntax="txt")

                embed.description += f"**Original Text:**\n{url} (result is too long to be displayed)\n\n"
            else:
                embed.description += f"**Original Text:**\n{res.original_text}\n\n"

        if len(res.translated_text) > 2000:
            url = await self.bot.mystbin.create_paste("translated-text.txt", res.translated_text, syntax="txt")

            embed.description += f"**Translated Text:**\n{url} (result is too long to be displayed)"
        else:
            embed.description += f"**Translated Text:**\n{res.translated_text}"

        embed.set_image(url=res.url)

        return embed

    @app_commands.command(name="image-to-text")
    @app_commands.describe(image="The attachment to be converted to text.",
                           url="The URL to an image to be converted to "
                               "text.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def image_to_text_slash(self, interaction: discord.Interaction, image: discord.Attachment = None,
                                  url: str = None):
        """
        Convert an image to text, known as the phrase OCR (Optical Character Recognition).
        """

        if url:
            url = url.strip()

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

        resp = await self.ocr_image(image)

        if isinstance(resp, discord.ui.View):
            return await interaction.followup.send('Result too long.', view=resp)
        else:
            return await interaction.followup.send(embed=resp)

    @commands.command(name="image-to-text", aliases=["ocr", "itt", "i2t", "image2text", "image-2-text", "imagetotext"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def image_to_text_command(self, ctx: commands.Context, *, image=None):
        """
        Convert an image to text, known as the phrase OCR (Optical Character Recognition).
        """

        image = await converter.ImageConverter().convert(ctx, image)

        if not image:
            return await ctx.send("Please send a attachment/URL to a image!")

        async with ctx.typing():
            resp = await self.ocr_image(image)

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

        resp = await self.ocr_image(url)

        if isinstance(resp, discord.ui.View):
            return await interaction.followup.send('Result too long.', view=resp, ephemeral=True)
        else:
            return await interaction.followup.send(embed=resp, ephemeral=True)

    @app_commands.command(name="translate-image")
    @app_commands.describe(language="The language for the text to be translated to",
                           image="The attachment to be converted to text then translated.",
                           url="The URL to an image to be converted to text then translated.")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def trocr_slash(self, interaction: discord.Interaction, language: str,
                          image: discord.Attachment = None, url: str = None):
        """
        Convert an image to text, then translates it to another language.
        """

        if url:
            url = url.strip()

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

        lang = await self.trocr.get_language(language)

        if not lang:
            return await interaction.response.send_message("Please provide a valid language!", ephemeral=True)

        await interaction.response.defer()

        embed = await self.translate_ocr(image, lang['code'])

        return await interaction.followup.send(embed=embed)

    @trocr_slash.autocomplete('language')
    async def trocr_autocomplete_language(self, interaction: discord.Interaction, current: str):
        amount = 25

        if not current:
            langs = await self.trocr.get_languages()
        else:
            langs = await self.trocr.search_language(current, amount)

        langs = langs[amount:]

        return [app_commands.Choice(name=lang['name'], value=lang['name']) for lang in langs][amount:]

    @commands.group(name="translate-image", aliases=["translate-ocr", "trocr", "trimg", "trim"],
                    invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def trocr_command(self, ctx: commands.Context, language: str, *, image=None):
        """
        Convert an image to text, then translates it to another language.
        """

        image = await converter.ImageConverter().convert(ctx, image)

        if not image:
            return await ctx.send("Please send a attachment/URL to a image!")

        lang = await self.trocr.get_language(language)

        if not lang:
            return await ctx.send("Please provide a valid language!")

        async with ctx.typing():
            embed = await self.translate_ocr(image, lang['code'])

            return await ctx.send(embed=embed)

    @app_commands.command(name="translate-image-languages")
    @app_commands.describe(query="The language you want to search for.")
    async def trocr_languages_slash(self, interaction: discord.Interaction, query: str = None):
        """
        Shows a list of languages that can be translated to.
        """

        await interaction.response.defer()

        if query:
            query = query.strip()

            lang = await self.trocr.search_language(query)

            if not lang:
                return await interaction.followup.send(f"Language `{query}` not found.", ephemeral=True)

            lang = lang[0]

            lang_code = lang['code']
            lang_name = lang['name']

            embed = discord.Embed(color=self.bot.color)
            embed.title = lang_name

            embed.description = f"**Language Name:** {lang_name}\n**Language Code:** {lang_code}"

            return await interaction.followup.send(embed=embed)

        ctx = await commands.Context.from_interaction(interaction)

        langs = await self.trocr.get_languages()

        source = TranslateOCRLanguagesPaginator(langs, per_page=10)
        menu = YodaMenuPages(source, delete_message_after=True)
        return await menu.start(ctx, channel=interaction.followup)

    @trocr_languages_slash.autocomplete('query')
    async def trocr_languages_autocomplete_query(self, interaction: discord.Interaction, current: str):
        amount = 25

        if not current:
            langs = await self.trocr.get_languages()
        else:
            langs = await self.trocr.search_language(current, amount)

        langs = langs[amount:]

        return [app_commands.Choice(name=lang['name'], value=lang['name']) for lang in langs][amount:]

    @trocr_command.command(name="languages")
    async def trocr_languages_slash(self, ctx: commands.Context, query: str = None):
        """
        Shows a list of languages that can be translated to.
        """

        if query:
            query = query.strip()

            lang = await self.trocr.search_language(query)

            if not lang:
                return await ctx.send(f"Language `{query}` not found.")

            lang = lang[0]

            lang_code = lang['code']
            lang_name = lang['name']

            embed = discord.Embed(color=self.bot.color)
            embed.title = lang_name

            embed.description = f"**Language Name:** {lang_name}\n**Language Code:** {lang_code}"

            return await ctx.send(embed=embed)

        langs = await self.trocr.get_languages()

        source = TranslateOCRLanguagesPaginator(langs, per_page=10)
        menu = YodaMenuPages(source, delete_message_after=True)
        return await menu.start(ctx)

    async def trocr_context_menu(self, interaction: discord.Interaction, message: discord.Message):
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
            return await interaction.response.send_message("There is no image!", ephemeral=True)

        class Modal(discord.ui.Modal, title="Translate OCR"):
            language = discord.ui.TextInput(label='Language', placeholder='Enter a Language')

            def __init__(self, cls):
                super().__init__()
                self.cls = cls
                
            async def on_submit(self, interaction: discord.Interaction):
                language = self.language.value

                lang = await self.cls.trocr.get_language(language)

                if not lang:
                    return await interaction.response.send_message("Please provide a valid language!", ephemeral=True)

                await interaction.response.defer(ephemeral=True)
                
                embed = await self.cls.translate_ocr(url, language)

                return await interaction.followup.send(embed=embed, ephemeral=True)

        return await interaction.response.send_modal(Modal(self))


async def setup(bot: commands.Bot):
    await bot.add_cog(OCR(bot))
