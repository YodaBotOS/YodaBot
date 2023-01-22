from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.context import Context
from core.openai import codex as core_codex
from core.openai import openai
from utils.converter import CodeblockConverter

if TYPE_CHECKING:
    from core.bot import Bot
    from core.openai import Codex as CodexClass


class Codex(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    async def cog_load(self):
        importlib.reload(core_codex)
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
    async def generate_code(self, ctx: Context, language: core_codex.SUPPORTED_LANGUAGES_LITERAL, *, prompt: str):
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

            embed.description = f"**Language:** {language}\n**Prompt:** {prompt}\n\n"

            if len(completion) > 3000:
                paste = await self.bot.mystbin.create_paste(
                    filename=f"code.{self.codex.FILE[language]}", content=completion
                )
                embed.description += f"Result: {paste} (code is too long to display)"
            else:
                embed.description += f"Result: ```{self.codex.FILE[language]}\n{completion}\n```"

            return await ctx.send(embed=embed)

    # If this would be a slash command
    @commands.command("explain-code", aliases=["explaincode", "excode"])
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def explain_code(
        self,
        ctx: Context,
        language: Optional[core_codex.SUPPORTED_LANGUAGES_LITERAL] = None,
        *,
        code: CodeblockConverter,
    ):
        """
        Explains code to you.

        Language can be either `Bash`, `C#`, `Go`, `Java`, `JavaScript`, `Python`, `Ruby`, `Rust`, `SQL`, or `TypeScript`. You can also provide a codeblock.

        Usage: `yoda explain-code <language> <code>`

        - `yoda explain-code Python print("Hello, World!")`
        - `yoda explain-code Javascript console.log("Hello, World!")`
        """

        lang = language or code[0]
        code = code[1]

        if not lang:
            ctx.command.reset_cooldown(ctx)
            raise commands.BadArgument("Language not provided")

        if lang not in core_codex.SUPPORTED_LANGUAGES:
            d = dict([(v, k) for k, v in self.codex.FILE.items()])

            if lang.lower() in d:
                lang = d[lang]
            else:
                d = self.codex.LOWERED_CHARS

                if lang.lower() in d:
                    lang = d[lang]
                else:
                    ctx.command.reset_cooldown(ctx)
                    raise commands.BadArgument("Language not supported")

        async with ctx.typing():
            explain = await self.codex.explain(lang, code, user=ctx.author.id)

            embed = discord.Embed(color=self.bot.color)
            embed.title = "Code Explaination Result:"

            embed.description = f"**Code: ({lang})** ```{lang.lower()}\n{code}\n```\n\n"

            if len(explain) > 3000:
                paste = await self.bot.mystbin.create_paste(filename=f"explaination.txt", content=explain)
                embed.description += f"Result: {paste} (code is too long to display)"
            else:
                embed.description += f"Result:\n{explain}"

            return await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Codex(bot))
