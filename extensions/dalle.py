import json
import asyncio
import importlib
import typing

import discord
from discord.ext import commands
from discord import app_commands

import config
from core import dalle2 as core_dalle2
from core.dalle2 import GeneratedImages, Size
from utils.paginator import YodaMenuPages
from utils.dalle import DalleImagesPaginator
from utils.converter import ImageConverter


class Dalle2(commands.Cog):
    """
    OpenAI Dalle 2
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx) -> bool:
        if ctx.author.id == 993492028300218388:
            return True

        return await self.bot.is_owner(ctx.author)

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

    async def cog_load(self):
        importlib.reload(core_dalle2)
        from core.dalle2 import GenerateArt

        self.dalle: GenerateArt = GenerateArt(config.OPENAI_KEY)

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
            result = self.dalle.create_image(prompt, amount, size=size, user=str(ctx.author.id))
        except Exception as e:
            if m:
                await m.delete()

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
            result = self.dalle.create_image_variations(img, amount, size=size, user=str(ctx.author.id))
        except Exception as e:
            if m:
                await m.delete()

            return await ctx.send(f"Something went wrong, try again later.", ephemeral=True)

        if m:
            await m.delete()

        source = DalleImagesPaginator(result.images, "Variations")
        menu = YodaMenuPages(source)

        await menu.start(ctx)

    @commands.hybrid_group('generate-art', aliases=['generate-image', 'generate-img', 'generate-images', 'dalle',
                                                    'dalle2', 'image-generator', 'imgen'],
                           invoke_without_command=True)
    @app_commands.describe(amount="Amount of images to generate",
                           size="Size of the image",
                           prompt="Prompt to generate images from")
    async def gen_art(self, ctx: commands.Context, amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
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

        if ctx.subcommand_passed is None:
            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.generate_image(ctx, prompt, amount, size)

    @gen_art.command('image', aliases=['img'])
    @app_commands.describe(amount="Amount of images to generate",
                           size="Size of the image",
                           prompt="Prompt to generate images from")
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

        if ctx.subcommand_passed is None:
            if size == "small":
                size = Size.SMALL
            elif size == "medium":
                size = Size.MEDIUM
            elif size == "large":
                size = Size.LARGE

            return await self.generate_image(ctx, prompt, amount, size)

    @gen_art.command('variations', aliases=['variation', 'var', 'similar'], with_app_command=False)
    async def gen_art_variations(self, ctx: commands.Context, amount: typing.Optional[commands.Range[int, 1, 10]] = 5,
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

        image = image or await ImageConverter(with_member=True, with_emoji=True).convert(ctx, image or '')

        if not image:
            return await ctx.send("Image not found.", ephemeral=True)

        if size == "small":
            size = Size.SMALL
        elif size == "medium":
            size = Size.MEDIUM
        elif size == "large":
            size = Size.LARGE

        return await self.variations(ctx, image, amount, size)


async def setup(bot: commands.Bot):
    await bot.add_cog(Dalle2(bot))
