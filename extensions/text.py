from __future__ import annotations

import importlib
import inspect
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands

import config
from core import openai as core_openai
from core.context import Context
from core.openai import OpenAI

if TYPE_CHECKING:
    from core.bot import Bot


class Text(commands.Cog):
    """
    Text-related commands
    """

    def __init__(self, bot: Bot):
        self.openai = None
        self.bot: Bot = bot

        self.grammar_ctx_menu = app_commands.ContextMenu(
            name=_T("Grammar Correction"),
            callback=self.check_grammar_context_menu,
        )
        self.bot.tree.add_command(self.grammar_ctx_menu)

        self.wordtune_ctx_menu = app_commands.ContextMenu(
            name=_T("Wordtune"),
            callback=self.word_tune_context_menu,
        )
        self.bot.tree.add_command(self.wordtune_ctx_menu)

    async def cog_load(self):
        importlib.reload(core_openai)
        from core.openai import OpenAI

        self.openai: OpenAI = OpenAI(config.OPENAI_KEY)
        self.bot.openai = self.openai

    async def cog_unload(self):
        del self.openai

        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def grammar_correction(
        self, user, text: str, rephrase: bool = False
    ) -> discord.Embed | tuple[str, Exception]:
        try:
            new_text = await self.openai.grammar_correction(text, user=user.id, rephrase=rephrase)
        except Exception as e:
            return "SOMETHING_WENT_WRONG", e

        is_same = text == new_text

        title = "Grammar Correction Result:"

        if rephrase:
            title = "Grammar Correction & Rephrasing Result:"

        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name=title, icon_url=user.display_avatar.url)
        embed.add_field(name="Original Text:", value=text, inline=False)
        embed.add_field(
            name="Corrected & Rephrased Text:" if rephrase else "Corrected Text:", value=new_text, inline=False
        )
        embed.add_field(name="Is The Same?", value=str(is_same), inline=False)

        return embed

    @app_commands.command(name=_T("check-grammar"))
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(text="The text to be checked for grammar.")
    @app_commands.choices(
        rephrase=[
            app_commands.Choice(name=_T("Rephrase"), value=str(True)),
            app_commands.Choice(name=_T("Don't Rephrase"), value=str(False)),
        ]
    )
    async def check_grammar_slash(self, interaction: discord.Interaction, text: str = None, rephrase: str = "False"):
        """
        Fix grammar mistakes in a text using AI.

        Note: only English texts are currently supported.
        """

        original_text = text

        rephrase = rephrase == "True"

        if text is None:

            class Modal(discord.ui.Modal):
                text = discord.ui.TextInput(
                    label="Text",
                    placeholder="Enter text to be checked for grammar.",
                    max_length=1000,
                )

                def __init__(self, *args, **kwargs):
                    self.func = kwargs.pop("func")
                    self.rephrase = kwargs.pop("rephrase")
                    super().__init__(*args, **kwargs)

                async def on_submit(self, inter: discord.Interaction):
                    original_text = self.text.value

                    if len(original_text) > 500:
                        return await interaction.response.send_message(
                            "Text must be less than 500 characters.", ephemeral=True
                        )

                    await inter.response.defer(thinking=True)

                    interaction = inter

                    original_text = discord.utils.escape_markdown(original_text)

                    embed = await self.func(interaction.user, original_text, self.rephrase)

                    if isinstance(embed, tuple):
                        interaction.client.tree.on_error(interaction, (embed[1], False))
                        return await interaction.followup.send(
                            f"Something went wrong. Try again later.", ephemeral=True
                        )

                    return await interaction.followup.send(embed=embed)

            return await interaction.response.send_modal(
                Modal(title="Grammar Correction", func=self.grammar_correction, rephrase=rephrase)
            )

        original_text = await commands.clean_content(escape_markdown=True).convert(
            await Context.from_interaction(interaction), original_text
        )

        if len(original_text) > 500:
            return await interaction.response.send_message("Text must be less than 500 characters.", ephemeral=True)

        await interaction.response.defer()

        embed = await self.grammar_correction(interaction.user, original_text, rephrase)

        if isinstance(embed, tuple):
            self.bot.tree.on_error(interaction, (embed[1], False))
            return await interaction.followup.send(f"Something went wrong. Try again later.", ephemeral=True)

        return await interaction.followup.send(embed=embed)

    @commands.command(
        "check-grammar",
        aliases=[
            "check_grammar",
            "checkgrammar",
            "grammar-correction",
            "grammar_correction",
            "grammar_check",
            "grammarcheck",
            "grammarcorrection",
            "grammar",
            "cg",
            "gc",
        ],
    )
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def check_grammar(self, ctx: Context, *, text: str = None):
        """
        Fix grammar mistakes in a text using AI.

        Note: only English texts are currently supported.
        """

        if text:
            rephrase = text.strip().endswith("--rephrase")
            text = text.replace("--rephrase", "").strip()
        else:
            rephrase = False

        if text is None:
            if not (ref := ctx.message.reference):
                raise commands.MissingRequiredArgument(
                    inspect.Parameter("text", inspect.Parameter.KEYWORD_ONLY, annotation=str)
                )

            text = ref.resolved.content

        if text is None:
            await ctx.send("Please enter text to be checked for grammar.")
            return

        original_text = await commands.clean_content(escape_markdown=True).convert(ctx, text)

        if len(original_text) > 500:
            return await ctx.send("Text must be less than 500 characters.")

        embed = await self.grammar_correction(ctx.author, original_text, rephrase)

        if isinstance(embed, tuple):
            self.bot.dispatch("command_error", ctx, embed[1], force=True, send_msg=False)
            return await ctx.send(f"Something went wrong. Try again later.")

        return await ctx.send(embed=embed)

    async def check_grammar_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        original_text = message.content

        if not original_text:
            return await interaction.response.send_message("No text found.")

        original_text = await commands.clean_content(escape_markdown=True).convert(
            await Context.from_interaction(interaction), original_text
        )

        if len(original_text) > 500:
            return await interaction.response.send_message("Text must be less than 500 characters.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)

        embed = await self.grammar_correction(interaction.user, original_text)

        if isinstance(embed, tuple):
            self.bot.tree.on_error(interaction, (embed[1], False))
            return await interaction.followup.send(f"Something went wrong. Try again later.", ephemeral=True)

        return await interaction.response.send(embed=embed)

    class TunesView(discord.ui.View):
        class TunesSelect(discord.ui.Select):
            def __init__(self, tunes: dict[str, str]) -> None:
                super().__init__(
                    min_values=1,
                    max_values=3,
                    placeholder="Select tune(s) to use.",
                    options=[
                        discord.SelectOption(label=tune, value=tune, emoji=emoji) for tune, emoji in tunes.items()
                    ],
                )

            async def callback(self, interaction: discord.Interaction):
                await interaction.response.send_message("Picked tunes: " + ", ".join(self.values), ephemeral=True)
                self.view.tunes = self.values
                self.view.stop()

        def __init__(self, tunes: dict[str, str], ctx) -> None:
            super().__init__(timeout=None)
            self.add_item(self.TunesSelect(tunes))
            self.tunes = []
            self.ctx = ctx

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if isinstance(self.ctx, commands.Context):
                author = self.ctx.author
            else:
                author = self.ctx.user

            if interaction.user.id != author.id:
                await interaction.response.send_message("You can't use this menu.", ephemeral=True)
                return False
            else:
                return True

    @commands.hybrid_command(name=_T("wordtune"), aliases=["wt"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @app_commands.describe(
        tunes=_T("The tune(s) to use. Don't specify one if you want to use multiple tunes"),
        amount=_T("The amount of sentences to generate."),
        text=_T("The text to be tuned."),
    )
    async def word_tune(
        self, ctx: Context, tunes: Optional[OpenAI.WORDTUNES_LITERAL] = None, amount: Optional[int] = 5, *, text: str
    ):
        """
        Tunes/Changes sentences into different feelings/moods.

        Note: only English texts are currently supported.
        """

        ori_text = await commands.clean_content(fix_channel_mentions=True).convert(ctx, text)

        if len(ori_text) > 500:
            return await ctx.send("Text must be less than 500 characters.")

        if not tunes:
            view = self.TunesView(OpenAI.WORDTUNES_EMOJIS, ctx)
            await ctx.send("Please select the tune(s) to use.", view=view)

            await view.wait()
            tunes = view.tunes
        else:
            if ctx.interaction:
                await ctx.interaction.response.defer()

            tunes = [tunes]

        r_text = await self.openai.wordtune(ori_text, tunes, amount, user=ctx.author.id)

        embed = discord.Embed()
        embed.set_author(name="Word Tune Results:", icon_url=ctx.author.avatar.url)
        embed.title = ", ".join(tunes)
        embed.add_field(name="Original Text:", value=text, inline=False)
        embed.add_field(name="Result:", value=r_text, inline=False)

        await ctx.send(embed=embed)

    async def word_tune_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        text = message.content

        if len(text) > 500:
            return await interaction.followup.send("Text must be less than 500 characters.", ephemeral=True)

        view = self.TunesView(OpenAI.WORDTUNES_EMOJIS, interaction)
        await interaction.response.send_message("Please select the tune(s) to use.", view=view, ephemeral=True)

        await view.wait()
        tunes = view.tunes

        r_text = await self.openai.wordtune(text, tunes, 5, user=interaction.user.id)

        embed = discord.Embed()
        embed.set_author(name="Word Tune Results:", icon_url=interaction.user.avatar.url)
        embed.title = ", ".join(tunes)
        embed.add_field(name="Original Text:", value=text, inline=False)
        embed.add_field(name="Result:", value=r_text, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Text(bot))
