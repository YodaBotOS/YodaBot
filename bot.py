import os
import re
import typing

import aiohttp
import mystbin
import discord
from discord.ext import commands
from discord import app_commands

import config
from core.ocr import OCR
from core.translate import Translate
from utils import converter

activity_name = f"\"{config.PREFIX}help\"" if isinstance(config.PREFIX, str) else f"\"{config.PREFIX[0]}help\""

bot = commands.Bot(
    command_prefix=config.PREFIX,
    intents=discord.Intents.all(),
    description=config.DESCRIPTION,
    activity=discord.Activity(type=discord.ActivityType.listening, name=activity_name),
    help_command=commands.MinimalHelpCommand(),
)


@bot.event
async def setup_hook():
    bot.color = discord.Colour(config.COLOR)  # C5D8FE
    bot.session = aiohttp.ClientSession()
    bot.mystbin = mystbin.Client(session=bot.session)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS_PATH

    # Init core modules
    bot.ocr = OCR(session=bot.session)
    bot.translate = Translate(config.PROJECT_ID, session=bot.session)
    await bot.translate.get_languages(force_call=True, add_to_cache=True)

    # Jishaku Environment Vars
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

    # Load cogs
    await bot.load_extension("jishaku")


@bot.event
async def on_ready():
    print(f"Bot ({bot.user} with ID {bot.user.id}) is ready and online!")


@bot.hybrid_command(aliases=["latency"])
async def ping(ctx: commands.Context):
    """
    Get the bot's latency.
    """
    return await ctx.send(f"Pong! `{round(bot.latency * 1000, 2)}ms`")


@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object],
               spec: typing.Optional[typing.Literal["~", "*", "^"]] = None):
    r"""
!sync -> Global sync
!sync ~ -> Sync current guild
!sync \* -> Copies all global app commands to current guild and syncs
!sync ^ -> Clears all commands from the current guild target and syncs (removes guild commands)
!sync id_1 id_2 -> Syncs guilds with id 1 and 2
    """

    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def ocr(image) -> discord.ui.View | discord.Embed:
    text = await bot.ocr.request(image)

    if len(text) > 4096:
        url = await bot.mystbin.post(text, syntax="text")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="View on mystb.in", url=url))

        return view

    embed = discord.Embed(color=bot.color)
    embed.title = "Image to Text (OCR) Result:"
    embed.description = text

    return embed


@bot.tree.command(name="image-to-text")
@app_commands.describe(image="The attachment to be converted to text.", url="The URL to an image to be converted to text.")
async def image_to_text(interaction: discord.Interaction, image: discord.Attachment = None, url: str = None):
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

    resp = await ocr(image)

    if isinstance(resp, discord.ui.View):
        return await interaction.followup.send('Result too long.', view=resp)
    else:
        return await interaction.followup.send(embed=resp)


@bot.command(name="image-to-text", aliases=["ocr", "itt", "i2t", "image2text", "image-2-text", "imagetotext"])
async def image_to_text(ctx: commands.Context, *, image=None):
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
        resp = await ocr(image)

        if isinstance(resp, discord.ui.View):
            return await ctx.send('Result too long.', view=resp)
        else:
            return await ctx.send(embed=resp)


bot.run(config.TOKEN)
