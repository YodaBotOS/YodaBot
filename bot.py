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

main_prefix = config.PREFIX if isinstance(config.PREFIX, str) else config.PREFIX[0]

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(config.PREFIX),
    intents=discord.Intents.all(),
    description=config.DESCRIPTION,
    activity=discord.Activity(type=discord.ActivityType.listening, name=f"\"{main_prefix}help\""),
    help_command=commands.MinimalHelpCommand(),
    strip_after_prefix=True,
)

bot.config = config
bot.main_prefix = main_prefix

extensions = [
    "jishaku",
    "extensions.ocr",
    "extensions.translate",
]


@bot.event
async def setup_hook():
    bot.color = discord.Colour(config.COLOR)  # C5D8FE
    bot.session = aiohttp.ClientSession()
    bot.mystbin = mystbin.Client(session=bot.session)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.GOOGLE_APPLICATION_CREDENTIALS_PATH

    # Jishaku Environment Vars
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

    # Load cogs
    for extension in extensions:
        await bot.load_extension(extension)


@bot.event
async def on_ready():
    print(f"Bot ({bot.user} with ID {bot.user.id}) is ready and online!")


@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if re.fullmatch(rf'<@!?{bot.user.id}>', msg.content):
        return await msg.channel.send(f"My prefix is `{main_prefix}`! You can also mention me!")

    return await bot.process_commands(msg)


@bot.event
async def on_message_edit(b, a):
    if b.content == a.content:
        return

    return await bot.process_commands(a)


@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"Error: {error}")

    raise error


@bot.tree.error
async def on_tree_error(interaction, error):
    try:
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(f"Error: {error}", ephemeral=True)

    # try:
    #     await interaction.response.defer()
    # except:
    #     pass
    #
    # try:
    #     await interaction.response.send_message(f"Error, please report: {error}", ephemeral=True)
    # except:
    #     await interaction.followup.send(f"Error, please report: {error}", ephemeral=True)

    raise error


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


bot.run(config.TOKEN)
