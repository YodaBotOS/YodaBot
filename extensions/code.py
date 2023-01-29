from __future__ import annotations

import asyncio
import functools
import importlib
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING, Optional

import discord
from async_timeout import timeout
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands

from core.context import Context
from core.openai import codex as core_codex
from core.openai import openai
from utils.converter import CodeblockConverter

# from guesslang.guess import Guess


if TYPE_CHECKING:
    from core.bot import Bot
    from core.openai import Codex as CodexClass


class CodeUtils(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    async def cog_load(self):
        importlib.reload(core_codex)
        from core.openai import codex

        openai.api_key = self.bot.config.OPENAI_KEY

        self.codex: CodexClass = codex.Codex()
        self.bot.codex = self.codex
        # self.guesslang = Guess()
        # self.bot.guesslang = self.guesslang

    async def cog_unload(self):
        del self.openai
        # del self.guesslang

    @commands.hybrid_command(_T("generate-code"), aliases=["generatecode", "gencode"])
    @app_commands.describe(
        language=_T("The language to generate code in"), prompt=_T("The prompt to generate code from")
    )
    @commands.max_concurrency(1, commands.BucketType.member)
    @commands.cooldown(1, 20, commands.BucketType.member)
    async def generate_code(self, ctx: Context, language: core_codex.SUPPORTED_LANGUAGES_LITERAL, *, prompt: str):
        """
        Generate code from a prompt.

        Language can be either `Bash`, `C#`, `Go`, `Java`, `JavaScript`, `Python`, `Ruby`, `Rust`, `SQL`, or `TypeScript`. (case-sensitive)

        Usage: `yoda generate-code <language> <prompt>`

        - `yoda generate-code Python Say "Hello, World!"`
        - `yoda generate-code Javascript Say "Hello, World!"`
        """

        async with ctx.typing():
            try:
                async with timeout(60):
                    completion = await self.codex.completion(language, prompt, user=ctx.author.id, n=1)
                    completion = completion[0]

                    embed = discord.Embed(color=self.bot.color)
                    embed.title = "Code Generation Result:"

                    embed.description = f"**Language:** {language}\n**Prompt:** {prompt}\n\n"

                    if len(completion) > 3000:
                        paste = await self.bot.mystbin.create_paste(
                            filename=f"code.{self.codex.FILE[language]}", content=completion
                        )
                        embed.description += f"**Result:** {paste} (Too long to display)"
                    else:
                        embed.description += f"**Result:** ```{self.codex.FILE[language]}\n{completion}\n```"

                    embed.set_footer(text="*Might not be accurate.")

                    return await ctx.send(embed=embed)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "Code Generation Timed out (>60 seconds). Something might be wrong or you are sending a prompt that is taking too long to generate.",
                    ephemeral=True,
                )

    # If this would be a slash command, it would be hard to insert the code.
    @commands.command("explain-code", aliases=["explaincode", "excode"])
    @commands.max_concurrency(1, commands.BucketType.member)
    @commands.cooldown(1, 20, commands.BucketType.member)
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
            try:
                async with timeout(60):
                    explain = await self.codex.explain(lang, code, user=ctx.author.id)

                    embed = discord.Embed(color=self.bot.color)
                    embed.title = "Code Explaination Result:"

                    if len(code) > 2000:
                        paste = await self.bot.mystbin.create_paste(
                            filename=f"code.{self.codex.FILE[language]}", content=code
                        )
                        embed.description = f"**Code: ({lang})** {paste} (Too long to display)\n\n"
                    else:
                        embed.description = f"**Code: ({lang})** ```{lang.lower()}\n{code}\n```\n\n"

                    if len(explain) > 2000:
                        paste = await self.bot.mystbin.create_paste(filename=f"explaination.txt", content=explain)
                        embed.description += f"**Result:** {paste} (Too long to display)"
                    else:
                        embed.description += f"**Result:**\n{explain}"

                    embed.set_footer(text="*Might not be accurate.")

                    return await ctx.send(embed=embed)
            except asyncio.TimeoutError:
                return await ctx.send(
                    "Code Explaination Timed out (>60 seconds). Something might be wrong or you are sending a code that is taking too long to explain.",
                    ephemeral=True,
                )

    # def predict(self, code):
    #     probs = self.guesslang.probabilities(code)
    #     probs.sort(key=lambda i: i[1], reverse=True)
    #     probs = probs[:5]

    #     sure_lang = self.guesslang.language_name(code) or probs[0][0]

    #     return probs, sure_lang

    # @commands.command("guess-language", aliases=["guesslanguage", "guesslang", "glang"])
    # @commands.max_concurrency(1, commands.BucketType.member)
    # @commands.cooldown(1, 20, commands.BucketType.member)
    # async def explain_code(
    #     self,
    #     ctx: Context,
    #     *,
    #     code: CodeblockConverter,
    # ):
    #     """
    #     Guesses the language of the code.

    #     You can also provide a codeblock or a raw text. Note that the language of the codeblock will be ignored (not used).

    #     Usage: `yoda guess-language <code>`

    #     - `yoda guess-language print("Hello, World!")`
    #     - `yoda guess-language console.log("Hello, World!")`
    #     """

    #     code = code[1]

    #     async with ctx.typing():
    #         with ProcessPoolExecutor() as pool:
    #             result = await self.bot.loop.run_in_executor(pool, functools.partial(self.predict, code))

    #         probs, sure_lang = result

    #         embed = discord.Embed(color=self.bot.color)
    #         embed.title = "Code Language Guessing Result:"

    #         entry = []

    #         for lang, probability in probs:
    #             spaces = 6 - len(lang)
    #             entry.append(f"{lang}{' '*spaces}: {probability * 100}%")

    #         embed.description = f"**Language:** `{sure_lang}`\n\n**Probability:** ```yml\n" + "\n".join(entry) + "\n```"

    #         embed.set_footer(text="*Might not be accurate.")

    #         await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CodeUtils(bot))
