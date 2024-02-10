from __future__ import annotations

import asyncio
import importlib
import json
import typing
import uuid
from io import BytesIO
from typing import TYPE_CHECKING

import discord
import openai
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands
from jishaku.functools import executor_function
from PIL import Image as PILImg

import config
from core import image as core_image
from core.context import Context
from core.image import GeneratedImages, Size
from core.image import firefly as core_firefly
from core.image import midjourney as core_midjourney
from core.image import utilities
from utils.converter import ImageConverter, SizeConverter
from utils.image import (
    DalleArtPaginator,
    DalleImagesPaginator,
    FireflyTextToImagePaginator,
    MidjourneyPaginator,
)
from utils.paginator import YodaMenuPages

if TYPE_CHECKING:
    from core.bot import Bot


class Image(commands.Cog):
    """
    Image utilities such as generating art from prompts or images!
    """

    def __init__(self, bot: Bot):
        self.image = None
        self.bot: Bot = bot

    async def text_check(self, text: str, *, raw: bool = False) -> dict | bool | None:
        """
        Just to be safe.

        This checks for text length (text should be `< TEXT_LIMIT`) and inappropriate text such as:
        - Insults
        - Threats
        - Sexual
        - etc.
        """

        url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"

        body = {
            "comment": {
                "text": text,
            },
            "requestedAttributes": {
                "TOXICITY": {
                    "scoreThreshold": 0.75,
                },
                "SEVERE_TOXICITY": {
                    "scoreThreshold": 0.75,
                },
                "IDENTITY_ATTACK": {
                    "scoreThreshold": 0.75,
                },
                "INSULT": {
                    "scoreThreshold": 0.75,
                },
                "PROFANITY": {
                    "scoreThreshold": 0.75,
                },
                "THREAT": {
                    "scoreThreshold": 0.75,
                },
                "SEXUALLY_EXPLICIT": {
                    "scoreThreshold": 0.75,
                },
                "FLIRTATION": {
                    "scoreThreshold": 0.75,
                },
            },
            "languages": ["en"],
        }

        params = {
            "key": config.PERSPECTIVE_KEY,
        }

        async with self.bot.session.post(
            url, data=json.dumps(body), params=params
        ) as resp:
            js = await resp.json()

            if raw:
                return js

            if js.get("attributeScores"):
                return False

        return True

    async def cog_load(self):
        importlib.reload(core_image)
        importlib.reload(core_firefly)
        from core.image import ImageUtilities
        from core.image.utilities import Upscaling

        self.image: ImageUtilities = ImageUtilities(
            (self.bot.cdn, "yodabot", "https://cdn.yodabot.xyz"),
            self.bot.session,
            (
                config.OPENAI_KEY,
                config.DREAM_KEY,
                config.REPLICATE_API_KEY,
                config.FIREFLY_KEY,
            ),
        )
        self.upscaling = Upscaling(config.REPLICATE_API_KEY, self.bot.session)
        # app_commands.choices(
        #     size=[
        #         app_commands.Choice(name=f"{k} ({v[0][0]}:{v[0][1]})", value=k)
        #         for k, v in self.image.firefly.SIZES.items()
        #     ]
        # )(self.firefly_slash)

    async def cog_unload(self):
        del self.image

    @executor_function
    def _convert_img(self, img):
        # idk tbh
        p_img = PILImg.open(BytesIO(img))
        if len(img) > 1024 * 1024 * 4:
            if p_img.size[0] > 1024 and p_img.size[1] > 1024:
                p_img = p_img.resize((1024, 1024))
            elif p_img.size[0] > 512 and p_img.size[1] > 512:
                p_img = p_img.resize((512, 512))
            else:
                p_img = p_img.resize((256, 256))

        new_img = BytesIO()
        p_img.save(new_img, format="PNG")
        new_img.seek(0)
        new_img = img.getvalue()

        return new_img

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
                return await ctx.send(
                    "Text seems inappropriate. Aborting.", ephemeral=True
                )

        try:
            result = await self.image.create_image(
                prompt, amount, size=size, user=str(ctx.author.id)
            )
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            if isinstance(e, openai.error.InvalidRequestError):
                return await ctx.send(f"Invalid prompt. {e}", ephemeral=True)

            return await ctx.send(
                f"Something went wrong, try again later.", ephemeral=True
            )

        if m:
            await m.delete()

        source = DalleImagesPaginator(result.images, "Image Generation", prompt)
        menu = YodaMenuPages(source)

        return await menu.start(ctx)

    async def variations(self, ctx, url, amount, size):
        async with self.bot.session.get(url) as resp:
            ori_img = await resp.read()

        img = await self._convert_img(ori_img)

        if ctx.interaction:
            await ctx.defer()
            m = None
        else:
            m = await ctx.send(f"⌛ Generating `{amount}` variation(s)...")

        try:
            result = await self.image.create_image_variations(
                img, amount, size=size, user=str(ctx.author.id)
            )
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            if isinstance(e, openai.error.InvalidRequestError):
                return await ctx.send(f"Invalid image. {e}", ephemeral=True)

            return await ctx.send(
                f"Something went wrong, try again later.", ephemeral=True
            )

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
            m = await ctx.send(
                f"⌛ Generating `{amount}` image(s) with style `{style.name}`..."
            )

        if not await self.bot.is_owner(ctx.author):
            check = await self.text_check(prompt)

            if not check:
                await m.delete()
                return await ctx.send(
                    "Text seems inappropriate. Aborting.", ephemeral=True
                )

        try:
            result = await self.image.style.generate(
                prompt, style, amount, height=height, width=width
            )
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            return await ctx.send(
                f"Something went wrong, try again later.", ephemeral=True
            )

        if m:
            await m.delete()

        source = DalleArtPaginator(result, prompt)
        menu = YodaMenuPages(source)

        return await menu.start(ctx)

    async def midjourney_imagine(self, ctx, prompt, amount, width, height):
        if ctx.interaction:
            await ctx.defer()
            m = None
        else:
            m = await ctx.send(f"⌛ Generating `{amount}` image(s)...")

        if not await self.bot.is_owner(ctx.author):
            check = await self.text_check(prompt)

            if not check:
                await m.delete()
                return await ctx.send(
                    "Text seems inappropriate. Aborting.", ephemeral=True
                )

        try:
            result = await self.image.midjourney.generate(
                prompt, amount, height=height, width=width
            )
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            return await ctx.send(
                f"Something went wrong, try again later.", ephemeral=True
            )

        if m:
            await m.delete()

        source = MidjourneyPaginator(result.output, prompt)
        menu = YodaMenuPages(source)

        return await menu.start(ctx)

    async def firefly_text_to_image(self, ctx, prompt, amount, size, styles=None):
        if ctx.interaction:
            await ctx.defer()
            m = None
        else:
            m = await ctx.send(f"⌛ Generating `{amount}` image(s)...")

        if not await self.bot.is_owner(ctx.author):
            check = await self.text_check(prompt)

            if not check:
                await m.delete()
                return await ctx.send(
                    "Text seems inappropriate. Aborting.", ephemeral=True
                )

        width = self.image.firefly.SIZES[size][1]
        height = self.image.firefly.SIZES[size][2]

        try:
            results = await self.image.firefly.text_to_image(
                prompt, amount, width=width, height=height, styles=styles
            )
        except Exception as e:
            if m:
                await m.delete()

            self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)

            return await ctx.send(
                f"Something went wrong, try again later.", ephemeral=True
            )

        if m:
            await m.delete()

        source = FireflyTextToImagePaginator(
            results, prompt, res_high=(size in ["Ultrawide", "Ultrawide Portrait"])
        )
        menu = YodaMenuPages(source)

        return await menu.start(ctx)

    MAX_CONCURRENCY = commands.MaxConcurrency(
        1, per=commands.BucketType.member, wait=False
    )

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
            await ctx.send(
                "You are already generating an image. Please wait until it's done.",
                ephemeral=True,
            )
            return

    @commands.group(
        "generate-art",
        aliases=[
            "generate-image",
            "generate-img",
            "generate-images",
            "dalle",
            "dalle2",
            "image-generator",
            "imgen",
        ],
        invoke_without_command=True,
    )
    async def gen_art_cmd(
        self,
        ctx: Context,
        amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
        size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large",
        *,
        prompt: str,
    ):
        """
        Generate an image from a prompt using DALL-E.

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

    @gen_art_cmd.command("image")
    async def gen_art2(
        self,
        ctx: Context,
        amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
        size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large",
        *,
        prompt: str,
    ):
        """
        Generate an image from a prompt using DALL-E.

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

    @gen_art_cmd.command("variations", aliases=["variation", "var", "similar"])
    async def gen_art_variations_cmd(
        self,
        ctx: Context,
        amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
        size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large",
        *,
        image: str = None,
    ):
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
            image = await ImageConverter(with_member=True, with_emoji=True).convert(
                ctx, image or ""
            )

            if not image:
                return await ctx.send(
                    "Please send an image or provide a URL.", ephemeral=True
                )

            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.variations(ctx, image, amount, size)

        await self.handle(ctx, main, amount, size, image)

    @gen_art_cmd.command("style")
    async def gen_art_style(
        self,
        ctx: Context,
        style: str = None,
        amount: typing.Optional[commands.Range[int, 1, 5]] = 1,
        size: typing.Optional[SizeConverter] = None,
        *,
        prompt: str = None,
    ):
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
            style = await self.image.style.get_style_from_name(style or "")

            if not style:
                styles = await self.image.style.get_styles(raw=True)
                embed = discord.Embed(
                    title="Styles",
                    description="Here are the available styles:\n\n",
                    color=self.bot.color,
                )

                for style in styles:
                    embed.description += f"- {style.name}\n"

                if original_style:
                    return await ctx.send(
                        "Style not found.", embed=embed, ephemeral=True
                    )
                else:
                    return await ctx.send(embed=embed, ephemeral=True)

            if not prompt:
                return await ctx.send("Please provide a prompt.", ephemeral=True)

            if size is not None:
                width, height = size

                if width > 1024 or height > 1024:
                    return await ctx.send(
                        "Maximum width and height is 1024 pixels.", ephemeral=True
                    )
            else:
                width, height = None, None

            return await self.generate_image_style(
                ctx, prompt, style, amount, width, height
            )

        await self.handle(ctx, main, prompt, style, amount, size)

    @commands.command("imagine", aliases=["midjourney", "mj"])
    async def midjourney_imagine_cmd(
        self,
        ctx: Context,
        amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
        size: typing.Optional[SizeConverter] = None,
        *,
        prompt: str,
    ):
        """
        Generate an image with the style of Midjourney V4.

        If amount is not provided, it would default to 5. Maximum is 10.

        Width is a max of 1024 pixels and height is a max of 1024 pixels.

        Usage: `yoda imagine [amount] [width x height] <prompt>`.
        """

        async def main(ctx, prompt, amount, size):
            if size is not None:
                width, height = size

                if width > 1024 or height > 1024:
                    return await ctx.send(
                        "Maximum width and height is 1024 pixels.", ephemeral=True
                    )
            else:
                width, height = 512, 512

            try:
                self.image.midjourney.check(amount, width, height)
            except ValueError as e:
                return await ctx.send(str(e).capitalize(), ephemeral=True)

            return await self.midjourney_imagine(ctx, prompt, amount, width, height)

        await self.handle(ctx, main, prompt, amount, size)

    # @commands.command("firefly", aliases=["ff"])
    # async def firefly_cmd(
    #     self,
    #     ctx: Context,
    #     amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
    #     size: core_firefly.FIREFLY_SIZES = "Square",
    #     *,
    #     prompt: str,
    # ):
    #     """
    #     Generate an image using Adobe Firefly AI.

    #     If amount is not provided, it would default to 5. Maximum is 10.

    #     Usage: `yoda firefly [amount] [width x height] <prompt>`.
    #     """

    #     async def main(ctx, prompt, amount, size):
    #         return await self.firefly_text_to_image(ctx, prompt, amount, size)

    #     await self.handle(ctx, main, prompt, amount, size)

    gen_art_slash = app_commands.Group(
        name=_T("generate-art"), description=_T("Generate an image from a prompt.")
    )

    @gen_art_slash.command(name=_T("image"))
    @app_commands.describe(
        amount=_T("Amount of images to generate"),
        size=_T("Size of the image"),
        prompt=_T("Prompt to generate images from"),
    )
    async def gen_art2_slash(
        self,
        interaction: discord.Interaction,
        prompt: str,
        amount: typing.Optional[app_commands.Range[int, 1, 10]] = 5,
        size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large",
    ):
        """
        Generate an image from a prompt using DALL-E.

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

        await self.handle(interaction, main, prompt, amount, size)

    @gen_art_slash.command(name=_T("variations"))
    @app_commands.describe(
        amount=_T("Amount of images to generate"),
        size=_T("The size of the image"),
        image=_T("Image to generate variations from"),
        url=_T("URL of the image to generate variations from"),
    )
    async def gen_art_variations_slash(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment = None,
        url: str = None,
        amount: typing.Optional[app_commands.Range[int, 1, 10]] = 5,
        size: typing.Optional[typing.Literal["small", "medium", "large"]] = "large",
    ):
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
                return await ctx.send(
                    "Please send an image or provide a URL.", ephemeral=True
                )

            if image and url:
                return await ctx.send(
                    "Please only send either an image or a URL.", ephemeral=True
                )

            image = url or image.url

            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.variations(ctx, image, amount, size)

        await self.handle(interaction, main, amount, size, image, url)

    @gen_art_slash.command(name=_T("style"))
    @app_commands.describe(
        style=_T("Style to apply to the image"),
        amount=_T("Amount of images to generate"),
        size=_T("Size of the image e.g 1024x1024"),
        prompt=_T("Prompt to generate images from"),
    )
    async def gen_art_style_slash(
        self,
        interaction: discord.Interaction,
        prompt: str = None,
        style: str = None,
        amount: typing.Optional[app_commands.Range[int, 1, 5]] = 1,
        size: typing.Optional[str] = None,
    ):
        """
        Generate an image from a prompt with styles applied.

        To get the list of styles available, use `yoda generate-art style`

        If amount is not provided, it would default to 1. Maximum is 5.

        Usage: `/generate-art style <style> [amount] [width x height] <prompt>`.

        - `/generate-art style:Synthwave prompt:Racing Car`
        - `/generate-art style:HD prompt:Forest`
        - `/generate-art style:Van Gogh size:1024x1024 prompt:A person sitting in a brown bench`
        - `/generate-art style:Mystical amount:5 prompt:Tall buildings`
        """

        async def main(ctx, prompt, style, amount, size):
            original_style = style
            style = await self.image.style.get_style_from_name(style or "")

            if not style:
                styles = await self.image.style.get_styles(raw=True)
                embed = discord.Embed(
                    title="Styles",
                    description="Here are the available styles:\n\n",
                    color=self.bot.color,
                )

                for style in styles:
                    embed.description += f"- {style.name}\n"

                if original_style:
                    return await ctx.send(
                        "Style not found.", embed=embed, ephemeral=True
                    )
                else:
                    return await ctx.send(embed=embed, ephemeral=True)

            if not prompt:
                return await ctx.send("Please provide a prompt.", ephemeral=True)

            if not size:
                return await ctx.send("Please provide a size.", ephemeral=True)

            try:
                width, height = await SizeConverter().convert(ctx, size)

                if width > 1024 or height > 1024:
                    return await ctx.send(
                        "Maximum width and height is 1024 pixels.", ephemeral=True
                    )
            except:
                if size:
                    return await ctx.send(
                        "Invalid size provided. Please enter a valid size e.g `1024x1024`",
                        ephemeral=True,
                    )

                width, height = None, None

            return await self.generate_image_style(
                ctx, prompt, style, amount, width, height
            )

        await self.handle(interaction, main, prompt, style, amount, size)

    @gen_art_style_slash.autocomplete("style")
    async def gen_art_style_slash_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        if not current:
            return [
                app_commands.Choice(name=style.name, value=style.name)
                for style in await self.image.style.get_styles(raw=True)
            ][:25]

        styles = []

        for style in await self.image.style.get_styles(raw=True):
            if current.lower() in style.name.lower():
                styles.append(app_commands.Choice(name=style.name, value=style.name))

        styles = styles[:25]

        return styles

    @app_commands.command(name=_T("imagine"))
    @app_commands.describe(
        prompt=_T("Prompt to generate images from"),
        amount=_T("Amount of images to generate, maximum is 10. Defaults to 5"),
        width=_T("Width of the image, defaults to 512"),
        height=_T("Height of the image, defaults to 512"),
    )
    async def midjourney_imagine_slash(
        self,
        interaction: discord.Interaction,
        prompt: str,
        amount: typing.Optional[app_commands.Range[int, 1, 10]] = 5,
        width: typing.Literal[128, 256, 512, 768, 1024] = 512,
        height: typing.Literal[128, 256, 512, 768, 1024] = 512,
    ):
        """
        Generate an image with the style of Midjourney V4.

        If amount is not provided, it would default to 5. Maximum is 10.

        Width is a max of 1024 pixels and height is a max of 1024 pixels.

        Usage: `/imagine [amount] [width x height] <prompt>`.
        """

        async def main(ctx, prompt, amount, size):
            if size is not None:
                width, height = size

                if width > 1024 or height > 1024:
                    return await ctx.send(
                        "Maximum width and height is 1024 pixels.", ephemeral=True
                    )
            else:
                width, height = 512, 512

            try:
                self.image.midjourney.check(amount, width, height)
            except ValueError as e:
                return await ctx.send(str(e).capitalize(), ephemeral=True)

            return await self.midjourney_imagine(ctx, prompt, amount, width, height)

        await self.handle(interaction, main, prompt, amount, (width, height))

    # @app_commands.command(name=_T("firefly"))
    # @app_commands.describe(
    #     prompt=_T("Prompt to generate images from"),
    #     amount=_T("Amount of images to generate, maximum is 10. Defaults to 5"),
    #     size=_T("Size of the image to be generated. Defaults to Square"),
    # )
    # async def firefly_slash(
    #     self,
    #     interaction: discord.Interaction,
    #     prompt: str,
    #     amount: typing.Optional[app_commands.Range[int, 1, 10]] = 5,
    #     size: str = "Square",
    # ):
    #     """
    #     Generate an image using Adobe Firefly AI.

    #     If amount is not provided, it would default to 5. Maximum is 10.

    #     Usage: `yoda firefly [amount] [width x height] <prompt>`.
    #     """

    #     async def main(ctx, prompt, amount, size):
    #         return await self.firefly_text_to_image(ctx, prompt, amount, size)

    #     await self.handle(interaction, main, prompt, amount, size)

    async def analyze_image(self, ctx, url):
        async with ctx.typing():
            async with self.bot.session.get(url) as resp:
                image = await resp.read()

            result = await self.image.analyze(image)

            embed = discord.Embed(title="Image Analysis Result:", color=self.bot.color)
            embed.set_image(url=url)

            embed.add_field(
                name="Adult Score:",
                value=f"""
**Is Adult Content:** `{'True' if result.adult.is_adult_content else 'False'}`
**Is Racy Content:** `{'True' if result.adult.is_racy_content else 'False'}`
**Is Gory Content:** `{'True' if result.adult.is_gory_content else 'False'}`

**Adult Score:** `{round(result.adult.adult_score, 1)}%`
**Racy Score:** `{round(result.adult.racy_score, 1)}%`
**Gore Score:** `{round(result.adult.gore_score, 1)}%`
            """,
                inline=False,
            )

            embed.add_field(
                name="Categories/Tags:",
                value=(
                    "- "
                    + "\n- ".join(
                        [
                            f"`{x.name}` - Confidence: `{round(x.confidence, 1)}%`"
                            for x in result.tags
                        ]
                    )
                    if result.tags
                    else "None"
                ),
                inline=False,
            )

            embed.add_field(
                name="Description/Caption:",
                value=(
                    "- "
                    + "\n- ".join(
                        [
                            f"`{x.text}` - Confidence: `{round(x.confidence, 1)}%`"
                            for x in result.captions
                        ]
                    )
                    if result.captions
                    else "None"
                ),
                inline=False,
            )

            embed.add_field(
                name="Color:",
                value=f"""
**Dominant Color Foreground:** `{result.color.dominant_color_foreground}`
**Dominant Color Background:** `{result.color.dominant_color_background}`
**Dominant Colors:** {', '.join([f'`{x}`' for x in result.color.dominant_colors]) if result.color.dominant_colors else 'None'}
**Accent Color:** `#{result.color.accent_color}`
**Is Black & White:** `{'True' if result.color.is_bw_img else 'False'}`
            """,
                inline=False,
            )

            embed.add_field(
                name="Image Type:",
                value=f"""
**Is Clip Art:** `{'True' if result.image_type.is_clip_art else 'False'}`
**Is Line Drawing:** `{'True' if result.image_type.is_line_drawing else 'False'}`
**Clip Art Type:** `{result.image_type.clip_art_type_describe.replace("-", " ").title()}`
            """,
                inline=False,
            )

            embed.add_field(
                name="Brands:",
                value=(
                    "- "
                    + "\n- ".join(
                        [
                            f"`{x.name}` - Confidence: `{round(x.confidence, 1)}%`"
                            for x in result.brands
                        ]
                    )
                    if result.brands
                    else "None"
                ),
                inline=False,
            )

            embed.add_field(
                name="Objects:",
                value=(
                    "- "
                    + "\n- ".join(
                        [
                            f"`{x.object}` - Confidence: `{round(x.confidence, 1)}%`"
                            for x in result.objects
                        ]
                    )
                    if result.objects
                    else "None"
                ),
                inline=False,
            )

            embed.add_field(
                name="Image Metadata/Properties:",
                value=f"""
**Width:** `{result.metadata.width}`
**Height:** `{result.metadata.height}`
            """,
                inline=False,
            )

        return embed

    MAX_CONCURRENCY_ANALYZE = commands.MaxConcurrency(
        1, per=commands.BucketType.member, wait=False
    )

    async def handle_analyze(self, ctx, func, *args, **kwargs):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.bot.get_context(ctx)

        try:
            await self.MAX_CONCURRENCY_ANALYZE.acquire(ctx)

            try:
                await func(ctx, *args, **kwargs)
            finally:
                await self.MAX_CONCURRENCY_ANALYZE.release(ctx)
        except commands.MaxConcurrencyReached:
            await ctx.send(
                "You are already analyzing an image. Please wait until it's done.",
                ephemeral=True,
            )
            return

    @commands.command(
        "analyze-image", aliases=["analyze-img", "analyze_img", "analyze_image"]
    )
    async def analyze_image_cmd(self, ctx, *, image: str = None):
        """
        Analyze an image including its colors, categories, brands, and more!

        Usage: `yoda analyze-image <image>`.

        - `yoda analyze-image <Attachment>`
        - `yoda analyze-image <URL>`
        - `yoda analyze-image <Emoji>`
        - `yoda analyze-image @Someone`
        """

        async def main(ctx, self, image):
            image = await ImageConverter(with_member=True, with_emoji=True).convert(
                ctx, image or ""
            )

            if not image:
                return await ctx.send("Please send an image or provide a URL.")

            embed = await self.analyze_image(ctx, image)

            return await ctx.send(embed=embed)

        return await self.handle_analyze(ctx, main, self, image)

    @app_commands.command(name=_T("analyze-image"))
    @app_commands.describe(
        image=_T("The image to analyze."), url=_T("The URL of the image to analyze.")
    )
    async def analyze_image_slash(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment = None,
        url: str = None,
    ):
        """
        Analyze an image including its colors, categories, brands, and more!

        Usage: `/analyze-image <image>`.

        - `/analyze-image <Attachment>`
        - `/analyze-image url:<URL>`
        """

        async def main(ctx, self, image):
            if image is None and url is None:
                return await ctx.send(
                    "Please send an image or provide a URL.", ephemeral=True
                )

            if image and url:
                return await ctx.send(
                    "Please only send either an image or a URL.", ephemeral=True
                )

            image = url or image.url

            embed = await self.analyze_image(ctx, image)

            return await ctx.send(embed=embed)

        return await self.handle_analyze(interaction, main, self, image)

    async def upscale_image(self, ctx, image, scale):
        async with ctx.typing():
            img = await self.upscaling(image, scale=scale)

            key = f"upscaling/{uuid.uuid4().hex}.png"

            self.bot.cdn.upload_fileobj(img, "yodabot", key)

            embed = discord.Embed(title="Image Upscaling Result:", color=self.bot.color)
            embed.set_image(url=f"https://cdn.yodabot.xyz/{key}")

            return embed

    MAX_CONCURRENCY_UPSCALE = commands.MaxConcurrency(
        1, per=commands.BucketType.member, wait=False
    )

    async def handle_upscale_image(self, ctx, func, *args, **kwargs):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.bot.get_context(ctx)

        try:
            await self.MAX_CONCURRENCY_UPSCALE.acquire(ctx)

            try:
                await func(ctx, *args, **kwargs)
            finally:
                await self.MAX_CONCURRENCY_UPSCALE.release(ctx)
        except commands.MaxConcurrencyReached:
            await ctx.send(
                "You are already upscaling an image. Please wait until it's done.",
                ephemeral=True,
            )
            return

    @commands.command(
        "upscale", aliases=["upscale-img", "upscale_img", "upscaleimg", "ui"]
    )
    async def upscale_cmd(
        self,
        ctx,
        scale: typing.Optional[commands.Range[int, 1, 10]] = 2,
        *,
        image: str = None,
    ):
        """
        Upscales an image to an insane resolution using AI.

        Warning: This might take a while to process and can result in a really huge filesize.

        Usage: `yoda upscale [scale] <image>`.

        - `yoda upscale 2 <Attachment>`
        - `yoda upscale 5 <URL>`
        - `yoda analyze-image 3 <Emoji>`
        - `yoda analyze-image 8 @Someone`
        """

        async def main(ctx, self, image):
            image = await ImageConverter(with_member=True, with_emoji=True).convert(
                ctx, image or ""
            )

            if not image:
                return await ctx.send("Please send an image or provide a URL.")

            embed = await self.upscale_image(ctx, image, scale)

            return await ctx.send(embed=embed)

        return await self.handle_upscale_image(ctx, main, self, image)

    @app_commands.command(name=_T("upscale"))
    @app_commands.describe(
        scale=_T("The higher, longer wait but the higher resolution"),
        image=_T("The image to be upscaled."),
        url=_T("The URL of the image to be upscaled."),
    )
    async def upscale_image_slash(
        self,
        interaction: discord.Interaction,
        scale: app_commands.Range[int, 1, 10] = 2,
        image: discord.Attachment = None,
        url: str = None,
    ):
        """
        Upscales an image to an insane resolution using AI.

        Warning: This might take a while to process and can result in a really huge filesize.

        Usage: `/upscale <image> <scale>`.

        - `/upscale <Attachment> 2`
        - `/upscale url:<URL> 3`
        """

        async def main(ctx, self, image):
            if image is None and url is None:
                return await ctx.send(
                    "Please send an image or provide a URL.", ephemeral=True
                )

            if image and url:
                return await ctx.send(
                    "Please only send either an image or a URL.", ephemeral=True
                )

            image = url or image.url

            embed = await self.upscale_image(ctx, image, scale)

            return await ctx.send(embed=embed)

        return await self.handle_upscale_image(interaction, main, self, image)


async def setup(bot: commands.Bot):
    await bot.add_cog(Image(bot))
