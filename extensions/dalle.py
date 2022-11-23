import json
import asyncio
import importlib
import typing

import openai
import discord
from discord.ext import commands
from discord import app_commands

import config
from core import dalle2 as core_dalle2
from core.dalle2 import GeneratedImages, Size
from utils.paginator import YodaMenuPages
from utils.dalle import DalleImagesPaginator, DalleArtPaginator
from utils.converter import ImageConverter, SizeConverter


class Art(commands.Cog):
    """
    Generate Art from prompts or images! 
    """

    def __init__(self, bot: commands.Bot):
        self.dalle = None
        self.bot = bot

    async def text_check(self, text: str, *, raw: bool = False) -> dict | bool | None:
        """
        Just to be safe.

        This checks for text length (text should be `< TEXT_LIMIT`) and inappropriate text such as:
        - Insults
        - Threats
        - Sexual
        - etc.
        """

        url = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        body = {
            'comment': {
                'text': text,
            },
            'requestedAttributes': {
                'TOXICITY': {
                    'scoreThreshold': 0.75,
                },
                'SEVERE_TOXICITY': {
                    'scoreThreshold': 0.75,
                },
                'IDENTITY_ATTACK': {
                    'scoreThreshold': 0.75,
                },
                'INSULT': {
                    'scoreThreshold': 0.75,
                },
                'PROFANITY': {
                    'scoreThreshold': 0.75,
                },
                'THREAT': {
                    'scoreThreshold': 0.75,
                },
                'SEXUALLY_EXPLICIT': {
                    'scoreThreshold': 0.75,
                },
                'FLIRTATION': {
                    'scoreThreshold': 0.75,
                }
            },
            "languages": ["en"],
        }

        params = {
            'key': config.PERSPECTIVE_KEY,
        }

        async with self.bot.session.post(url, data=json.dumps(body), params=params) as resp:
            js = await resp.json()

            if raw:
                return js

            if js.get('attributeScores'):
                return False

        return True

    async def init(self):
        importlib.reload(core_dalle2)
        from core.dalle2 import GenerateArt

        self.dalle: GenerateArt = GenerateArt((self.bot.cdn, "yodabot", "https://cdn.yodabot.xyz"),
                                              self.bot.session, (config.OPENAI_KEY, config.DREAM_KEY))
        
        # Hacky way, ik, idk how to do it the proper/better way.
        styles = [x.name for x in await self.dalle.style.get_styles(raw=True)]
        choices = [app_commands.Choice(name=x, value=x) for x in styles]
        
        app_commands.choices(style=choices)(self.gen_art_style_slash)

    async def cog_unload(self):
        del self.dalle

    async def generate_image(self, ctx, prompt, amount, size):
        if ctx.interaction:
            await ctx.defer()
            m = None
        else:
            m = await ctx.send(f"⌛ Generating `{amount}` image(s)...")

        if not await self.bot.is_owner(ctx.author):
            check = await self.text_check(prompt)

            if not check:
                await m.delete()
                return await ctx.send("Text seems inappropriate. Aborting.", ephemeral=True)

        try:
            result = await self.dalle.create_image(prompt, amount, size=size, user=str(ctx.author.id))
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            if isinstance(e, openai.error.InvalidRequestError):
                return await ctx.send(f"Invalid prompt. {e}", ephemeral=True)

            return await ctx.send(f"Something went wrong, try again later.", ephemeral=True)

        if m:
            await m.delete()

        source = DalleImagesPaginator(result.images, "Image Generation", prompt)
        menu = YodaMenuPages(source)

        return await menu.start(ctx)

    async def variations(self, ctx, url, amount, size):
        async with self.bot.session.get(url) as resp:
            img = await resp.read()

        if ctx.interaction:
            await ctx.defer()
            m = None
        else:
            m = await ctx.send(f"⌛ Generating `{amount}` variation(s)...")

        try:
            result = await self.dalle.create_image_variations(img, amount, size=size, user=str(ctx.author.id))
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            if isinstance(e, openai.error.InvalidRequestError):
                return await ctx.send(f"Invalid image. {e}", ephemeral=True)

            return await ctx.send(f"Something went wrong, try again later.", ephemeral=True)

        if m:
            await m.delete()

        source = DalleImagesPaginator(result.images, "Variations")
        menu = YodaMenuPages(source)

        await menu.start(ctx)

    async def generate_image_style(self, ctx, prompt, style, amount, width, height):
        if ctx.interaction:
            await ctx.defer()
            m = None
        else:
            m = await ctx.send(f"⌛ Generating `{amount}` image(s) with style `{style.name}`...")

        if not await self.bot.is_owner(ctx.author):
            check = await self.text_check(prompt)

            if not check:
                await m.delete()
                return await ctx.send("Text seems inappropriate. Aborting.", ephemeral=True)

        try:
            result = await self.dalle.style.generate(prompt, style, amount, height=height, width=width)
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            return await ctx.send(f"Something went wrong, try again later.", ephemeral=True)

        if m:
            await m.delete()

        source = DalleArtPaginator(result, prompt)
        menu = YodaMenuPages(source)

        return await menu.start(ctx)

    MAX_CONCURRENCY = commands.MaxConcurrency(1, per=commands.BucketType.user, wait=False)

    async def handle(self, ctx, func, *args, **kwargs):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.bot.get_context(ctx)

        try:
            await self.MAX_CONCURRENCY.acquire(ctx)

            try:
                await func(ctx, *args, **kwargs)
            finally:
                await self.MAX_CONCURRENCY.release(ctx)
        except commands.MaxConcurrencyReached:
            await ctx.send("You are already generating an image. Please wait until it's done.", ephemeral=True)
            return

    @commands.group('generate-art', aliases=['generate-image', 'generate-img', 'generate-images', 'dalle', 'dalle2',
                                             'image-generator', 'imgen'],
                    invoke_without_command=True)
    async def gen_art_cmd(self, ctx: commands.Context, amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
                          size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large", *, prompt: str):
        """
        Generate an image from a prompt.

        If amount is not provided, it would default to 5. Maximum is 10.

        Usage: `yoda generate-art [amount] [size] <prompt>`.

        - `yoda generate-art 2 A cute dog standing next to a person`
        - `yoda generate-art A cat fighting with a dog`
        - `yoda generate-art small A person sitting in a brown bench`
        - `yoda generate-art 5 large A dog sleeping on a bed`
        """

        async def main(ctx, prompt, amount, size):
            if ctx.subcommand_passed is None:
                if size == "small":
                    size = Size.SMALL
                elif size == "medium":
                    size = Size.MEDIUM
                elif size == "large":
                    size = Size.LARGE

                return await self.generate_image(ctx, prompt, amount, size)

        await self.handle(ctx, main, prompt, amount, size)

    @gen_art_cmd.command('image')
    async def gen_art2(self, ctx: commands.Context, amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
                       size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large", *, prompt: str):
        """
        Generate an image from a prompt.

        If amount is not provided, it would default to 5. Maximum is 10.

        Usage: `yoda generate-art image [amount] [size] <prompt>`.

        - `yoda generate-art image 2 A cute dog standing next to a person`
        - `yoda generate-art image A cat fighting with a dog`
        - `yoda generate-art image small A person sitting in a brown bench`
        - `yoda generate-art image 5 large A dog sleeping on a bed`
        """

        async def main(ctx, prompt, amount, size):
            if ctx.subcommand_passed is None:
                if size == "small":
                    size = Size.SMALL
                elif size == "medium":
                    size = Size.MEDIUM
                elif size == "large":
                    size = Size.LARGE

                return await self.generate_image(ctx, prompt, amount, size)

        await self.handle(ctx, main, prompt, amount, size)

    @gen_art_cmd.command('variations', aliases=['variation', 'var', 'similar'])
    async def gen_art_variations_cmd(self, ctx: commands.Context,
                                     amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
                                     size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large", *,
                                     image: str = None):
        """
        Gets a list of variations of an image provided.

        If amount is not provided, it would default to 5. Maximum is 10.

        Image can be an attachment, a reply to another person, a sticker, a link, etc.

        Usage: `yoda generate-art variations [amount] [size] <image>`.

        - `yoda generate-art variations <url>`
        - `yoda generate-art variations 2 <url>`
        - `yoda generate-art variations 5 large <attachment>`
        """

        async def main(ctx, amount, size, image):
            image = image or await ImageConverter(with_member=True, with_emoji=True).convert(ctx, image or '')

            if not image:
                return await ctx.send("Please send an image or provide a URL.", ephemeral=True)

            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.variations(ctx, image, amount, size)

        await self.handle(ctx, main, amount, size, image)

    @gen_art_cmd.command('style')
    async def gen_art_style(self, ctx: commands.Context, style: str = None,
                            amount: typing.Optional[commands.Range[int, 1, 5]] = 1,
                            size: typing.Optional[SizeConverter] = None, *, prompt: str = None):
        """
        Generate an image from a prompt with styles applied.

        To get the list of styles available, use `yoda generate-art style`

        If amount is not provided, it would default to 1. Maximum is 5.

        Usage: `yoda generate-art style <style> [amount] [width x height] <prompt>`.

        - `yoda generate-art style Synthwave Racing Car`
        - `yoda generate-art style HD Forest`
        - `yoda generate-art style "Van Gogh" 1024x1024 A person sitting in a brown bench`
        - `yoda generate-art style Mystical 5 Tall buildings`
        """

        async def main(ctx, prompt, style, amount, size):
            original_style = style
            style = await self.dalle.style.get_style_from_name(style or '')

            if not style:
                styles = await self.dalle.style.get_styles(raw=True)
                embed = discord.Embed(title="Styles", description="Here are the available styles:\n\n",
                                      color=self.bot.color)

                for style in styles:
                    embed.description += f"- {style.name}\n"

                if original_style:
                    return await ctx.send("Style not found.", embed=embed, ephemeral=True)
                else:
                    return await ctx.send(embed=embed, ephemeral=True)

            if not prompt:
                return await ctx.send("Please provide a prompt.", ephemeral=True)

            if size is not None:
                width, height = size
                
                if width > 1024 or height > 1024:
                    return await ctx.send("Maximum width and height is 1024 pixels.", ephemeral=True)
            else:
                width, height = None, None

            return await self.generate_image_style(ctx, prompt, style, amount, width, height)

        await self.handle(ctx, main, prompt, style, amount, size)

    gen_art_slash = app_commands.Group(name="generate-art", description="Generate an image from a prompt.")

    @gen_art_slash.command(name='image')
    @app_commands.describe(amount="Amount of images to generate",
                           size="Size of the image",
                           prompt="Prompt to generate images from")
    async def gen_art2_slash(self, interaction: discord.Interaction, prompt: str,
                             amount: typing.Optional[app_commands.Range[int, 1, 10]] = 5,
                             size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large"):
        """
        Generate an image from a prompt.

        If amount is not provided, it would default to 5. Maximum is 10.

        Usage: `/generate-art image [amount] [size] <prompt>`.

        - `/generate-art image 2 A cute dog standing next to a person`
        - `/generate-art image A cat fighting with a dog`
        - `/generate-art image small A person sitting in a brown bench`
        - `/generate-art image 5 large A dog sleeping on a bed`
        """

        async def main(ctx, prompt, amount, size):
            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.generate_image(ctx, prompt, amount, size)

        await self.handle(interaction, main, prompt, amount, size)  # type: ignore

    @gen_art_slash.command(name='variations')
    @app_commands.describe(amount="Amount of images to generate",
                           size="The size of the image",
                           image="Image to generate variations from",
                           url="URL of the image to generate variations from")
    async def gen_art_variations_slash(self, interaction: discord.Interaction, image: discord.Attachment = None,
                                       url: str = None, amount: typing.Optional[app_commands.Range[int, 1, 10]] = 5,
                                       size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large"):
        """
        Gets a list of variations of an image provided.

        If amount is not provided, it would default to 5. Maximum is 10.

        Image can be an attachment, a reply to another person, a sticker, a link, etc.

        Usage: `/generate-art variations [amount] [size] <image>`.

        - `/generate-art variations <url>`
        - `/generate-art variations 2 <url>`
        - `/generate-art variations 5 large <attachment>`
        """

        async def main(ctx, amount, size, image, url):
            if image is None and url is None:
                return await ctx.send("Please send an image or provide a URL.", ephemeral=True)

            if image and url:
                return await ctx.send("Please only send either an image or a URL.", ephemeral=True)

            image = url or image.url

            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.variations(ctx, image, amount, size)

        await self.handle(interaction, main, amount, size, image, url)  # type: ignore

    @gen_art_slash.command(name='style')
    @app_commands.describe(style="Style to apply to the image",
                           amount="Amount of images to generate",
                           size="Size of the image e.g 1024x1024",
                           prompt="Prompt to generate images from")
    async def gen_art_style_slash(self, ctx: commands.Context, prompt: str = None, style: str = None,
                                  amount: typing.Optional[app_commands.Range[int, 1, 5]] = 1,
                                  size: typing.Optional[str] = None):
        """
        Generate an image from a prompt with styles applied.

        To get the list of styles available, use `yoda generate-art style`

        If amount is not provided, it would default to 1. Maximum is 5.

        Usage: `yoda generate-art style <style> [amount] [width x height] <prompt>`.

        - `yoda generate-art style Synthwave Racing Car`
        - `yoda generate-art style HD Forest`
        - `yoda generate-art style "Van Gogh" 1024x1024 A person sitting in a brown bench`
        - `yoda generate-art style Mystical 5 Tall buildings`
        """

        async def main(ctx, prompt, style, amount, size):
            original_style = style
            style = await self.dalle.style.get_style_from_name(style or '')

            if not style:
                styles = await self.dalle.style.get_styles(raw=True)
                embed = discord.Embed(title="Styles", description="Here are the available styles:\n\n",
                                      color=self.bot.color)

                for style in styles:
                    embed.description += f"- {style.name}\n"

                if original_style:
                    return await ctx.send("Style not found.", embed=embed, ephemeral=True)
                else:
                    return await ctx.send(embed=embed, ephemeral=True)

            if not prompt:
                return await ctx.send("Please provide a prompt.", ephemeral=True)

            if not size:
                return await ctx.send("Please provide a size.", ephemeral=True)

            try:
                width, height = await SizeConverter().convert(ctx, size)

                if width > 1024 or height > 1024:
                    return await ctx.send("Maximum width and height is 1024 pixels.", ephemeral=True)
            except:
                if size:
                    return await ctx.send("Invalid size provided. Please enter a valid size e.g `1024x1024`",
                                          ephemeral=True)

                width, height = None, None

            return await self.generate_image_style(ctx, prompt, style, amount, width, height)

        await self.handle(ctx, main, prompt, style, amount, size)


async def setup(bot: commands.Bot):
    cog = Art(bot)
    await cog.init()

    await bot.add_cog(cog)
