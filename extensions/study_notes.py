import typing
import asyncio
import importlib

import discord
from discord.ext import commands
from discord import app_commands

import config
from core import openai as core_openai


class StudyNotes(commands.Cog):
    """
    Chat with an AI
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        importlib.reload(core_openai)
        from core.openai import OpenAI

        self.openai: OpenAI = OpenAI(config.OPENAI_KEY)

    async def cog_unload(self):
        del self.openai

    @commands.command('study-notes')
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def study_notes(self, ctx: commands.Context, amount: typing.Optional[commands.Range[int, 1, 10]] = 5, *, topic: str):
        """
        Generate study notes about a certain topic
        """

        try:
            notes = self.openai.study_notes(topic, amount=amount)
        except Exception as e:
            return await ctx.send(f"Something went wrong, try again later.")

        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name="Study Notes:", icon_url=ctx.author.display_avatar.url)
        embed.title = f"Study Notes about {topic}:"
        embed.description = notes

        return await ctx.send(embed=embed)

    STUDY_NOTES_SLASH_MAX_CONCURRENCY = commands.MaxConcurrency(1, per=commands.BucketType.user, wait=False)

    @app_commands.command(name='study-notes')
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def study_notes_slash(self, interaction: discord.Interaction, topic: str,
                                amount: app_commands.Range[int, 1, 10] = 5):
        """
        Generate study notes about a certain topic
        """

        # As of right now, app_commands does not support max_concurrency, so we need to handle it ourselves in the
        # callback.
        ctx = await commands.Context.from_interaction(interaction)
        await self.STUDY_NOTES_SLASH_MAX_CONCURRENCY.acquire(ctx.message)

        await interaction.response.defer()

        try:
            try:
                notes = self.openai.study_notes(topic, amount=amount)
            except Exception as e:
                return await interaction.followup.send(f"Something went wrong, try again later.", ephemeral=True)

            embed = discord.Embed(color=self.bot.color)
            embed.set_author(name="Study Notes:", icon_url=ctx.author.display_avatar.url)
            embed.title = f"Study Notes about {topic}:"
            embed.description = notes

            return await interaction.followup.send(embed=embed)
        finally:
            await self.STUDY_NOTES_SLASH_MAX_CONCURRENCY.release(ctx.message)


async def setup(bot):
    await bot.add_cog(StudyNotes(bot))
