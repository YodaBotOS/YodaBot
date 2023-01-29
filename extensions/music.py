from __future__ import annotations

import typing
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands

from core.context import Context
from core.music import *
from utils.converter import AttachmentConverter
from utils.lyrics import *

if TYPE_CHECKING:
    from core.bot import Bot


class Music(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.lyrics = Lyrics(loop=self.bot.loop, session=self.bot.session)
        self.gpred = GenrePrediction(session=self.bot.session)

    @commands.hybrid_command(_T("lyrics"), aliases=["lyric"])
    @app_commands.describe(query=_T("The song's lyrics to search for."))
    async def lyrics(self, ctx: Context, *, query: str):
        """
        Search for lyrics of a song.
        """

        async with ctx.typing():
            res = await self.lyrics.search(query)

            if res == LyricResult.empty() or not res.lyrics:
                return await ctx.send("No results found.")

            pages = paginate_lyric_result(res)

            source = LyricsPaginator(pages)

            menu = YodaMenuPages(source=source)

            return await menu.start(ctx)

    @lyrics.autocomplete("query")
    async def lyrics_query_autocomplete(self, interaction: discord.Interaction, current: str):
        if not current:
            return []

        suggestions = await self.lyrics.autocomplete(current, slash_autocomplete=True)

        return suggestions

    async def predict_genre(self, file: str | discord.Attachment, mode: str):
        if isinstance(file, discord.Attachment):
            file = await file.read()

        res, start, end, elapsed = await self.gpred(file, mode=mode)

        if not res:
            return "NO_RESULT"

        embed = discord.Embed(color=self.bot.color)
        embed.title = "Genre Prediction"

        for genre, confidence in res.items():
            embed.add_field(
                name=f"**Genre:** `{genre.title()}`",
                value=f"**Confidence:** `{confidence}%`",
            )

        embed.set_footer(text=f"Time Elapsed: {round(elapsed, 1)}s\nPowered by Yoda API")

        return embed

    PREDICT_GENRE_MAX_CONCURRENCY = commands.MaxConcurrency(1, per=commands.BucketType.member, wait=False)

    @commands.command(
        "predict-genre",
        aliases=[
            "genre-predict",
            "genre-prediction",
            "pg",
            "gp",
            "predictgenre",
            "genrepredict",
            "genreprediction",
        ],
    )
    async def predict_genre_cmd(
        self,
        ctx: Context,
        mode: typing.Optional[typing.Literal["fast", "best"]] = "best",
        *,
        file: AttachmentConverter,
    ):
        """
        Predict the genre of a song.
        """

        await self.PREDICT_GENRE_MAX_CONCURRENCY.acquire(ctx.message)

        try:
            async with ctx.typing():
                m = await ctx.send("Getting results... Please wait.")

                result = await self.predict_genre(file, mode=mode)

                if result == "NO_RESULT":
                    return await ctx.send("No results found.")

                await m.delete()

                return await ctx.send(embed=result)
        finally:
            await self.PREDICT_GENRE_MAX_CONCURRENCY.release(ctx.message)

    @app_commands.command(name=_T("predict-genre"))
    @app_commands.describe(
        file=_T("The audio file to check the genre for."),
        url=_T("The URL of the audio file to check the genre for."),
        mode=_T("The mode of the genre check. Best is slow."),
    )
    async def predict_genre_slash(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment = None,
        url: str = None,
        mode: typing.Literal["fast", "best"] = "best",
    ):
        """
        Predict the genre of a song.
        """

        ctx = await Context.from_interaction(interaction)
        await self.PREDICT_GENRE_MAX_CONCURRENCY.acquire(ctx.message)

        try:
            if file and url:
                return await interaction.response.send_message(
                    "You can only provide either one of `file` or `url`, " "not both.",
                    ephemeral=True,
                )
            elif not file and not url:
                return await interaction.response.send_message(
                    "You must provide either `file` or `url`.", ephemeral=True
                )

            await interaction.response.defer()

            file = file or url

            result = await self.predict_genre(file, mode=mode)

            if result == "NO_RESULT":
                return await interaction.followup.send("No results found.")

            return await interaction.followup.send(embed=result)
        finally:
            await self.PREDICT_GENRE_MAX_CONCURRENCY.release(ctx.message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
