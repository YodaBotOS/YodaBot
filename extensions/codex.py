from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.context import Context
from core.openai import codex, openai

if TYPE_CHECKING:
    from core.bot import Bot
    from core.openai import Codex as CodexClass


class Codex(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    async def cog_load(self):
        importlib.reload(codex)
        from core.openai import codex

        openai.api_key = self.bot.config.OPENAI_KEY

        self.codex: CodexClass = codex.Codex()
        self.bot.codex = self.codex

    async def cog_unload(self):
        del self.openai

    @commands.hybrid_command("generate-code", aliases=["generatecode", "gencode"])
    @app_commands.describe(language="The language to generate code in", prompt="The prompt to generate code from")
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def generate_code(self, ctx: Context, language: codex.SUPPORTED_LANGUAGES_LITERAL, *, prompt: str):
        """
        Generate code from a prompt.

        Language can be either `Bash`, `C#`, `Go`, `Java`, `JavaScript`, `Python`, `Ruby`, `Rust`, `SQL`, or `TypeScript`. (case-sensitive)

        Usage: `yoda generate-code <language> <prompt>`

        - `yoda generate-code Python Say "Hello, World!"`
        - `yoda generate-code Javascript Say "Hello, World!"`
        """

        async with ctx.typing():
            completion = await self.codex.completion(language, prompt, user=ctx.author.id, n=1)
            completion = completion[0]

            embed = discord.Embed(color=self.bot.color)
            embed.title = "Code Generation Result:"
            embed.description = f"**Language:** {language}\n**Prompt:** {prompt}\n\n```{self.codex.CODEBLOCK[language]}\n{completion}\n```"

            return await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Codex(bot))
