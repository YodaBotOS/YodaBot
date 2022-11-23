import inspect
import importlib

import discord
from discord.ext import commands
from discord import app_commands

import config
from core import openai as core_openai


class GrammarCorrection(commands.Cog):
    """
    Grammar Correction
    """

    def __init__(self, bot: commands.Bot):
        self.openai = None
        self.bot = bot

        self.ctx_menu = app_commands.ContextMenu(
            name="Grammar Correction",
            callback=self.check_grammar_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_load(self):
        importlib.reload(core_openai)
        from core.openai import OpenAI

        self.openai: OpenAI = OpenAI(config.OPENAI_KEY)

    async def cog_unload(self):
        del self.openai

        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def grammar_correction(self, user, text: str) -> discord.Embed | tuple[str, Exception]:
        try:
            new_text = self.openai.grammar_correction(text)
        except Exception as e:
            return "SOMETHING_WENT_WRONG", e

        is_same = text == new_text

        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name="Grammar Correction Result:", icon_url=user.display_avatar.url)
        embed.add_field(name="Original Text:", value=text, inline=False)
        embed.add_field(name="Corrected Text:", value=new_text, inline=False)
        embed.add_field(name="Is The Same?", value=str(is_same), inline=False)

        return embed

    @app_commands.command(name="check-grammar")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(text="The text to be checked for grammar.")
    async def check_grammar_slash(self, interaction: discord.Interaction, text: str = None):
        """
        Fix grammar mistakes in a text using AI.

        Note: only English texts are currently supported.
        """

        original_text = text

        if text is None:
            class Modal(discord.ui.Modal):
                text = discord.ui.TextInput(label="Text", placeholder="Enter text to be checked for grammar.",
                                            max_length=1000)

                def __init__(self, *args, **kwargs):
                    self.func = kwargs.pop("func")
                    super().__init__(*args, **kwargs)

                async def on_submit(self, inter: discord.Interaction):
                    await inter.response.defer(thinking=True)

                    interaction = inter
                    original_text = self.text.value

                    original_text = discord.utils.escape_markdown(original_text)

                    embed = await self.func(interaction.user, original_text)

                    if isinstance(embed, tuple):
                        interaction.client.tree.on_error(interaction, (embed[1], False))  # type: ignore
                        return await interaction.followup.send(f"Something went wrong. Try again later.",
                                                               ephemeral=True)

                    return await interaction.followup.send(embed=embed)

            return await interaction.response.send_modal(Modal(title="Grammar Correction",
                                                               func=self.grammar_correction))
        else:
            await interaction.response.defer()

        original_text = await commands.clean_content(escape_markdown=True).convert(
            await commands.Context.from_interaction(interaction), original_text
        )

        embed = await self.grammar_correction(interaction.user, original_text)

        if isinstance(embed, tuple):
            self.bot.tree.on_error(interaction, (embed[1], False))  # type: ignore
            return await interaction.followup.send(f"Something went wrong. Try again later.", ephemeral=True)

        return await interaction.followup.send(embed=embed)

    @commands.command("check-grammar", aliases=["check_grammar", "checkgrammar", "grammar-correction",
                                                "grammar_correction", "grammar_check", "grammarcheck",
                                                "grammarcorrection", "grammar", "cg", "gc"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def check_grammar(self, ctx: commands.Context, *, text: str = None):
        """
        Fix grammar mistakes in a text using AI.

        Note: only English texts are currently supported.
        """

        if text is None:
            if not (ref := ctx.message.reference):
                raise commands.MissingRequiredArgument(inspect.Parameter('text', inspect.Parameter.KEYWORD_ONLY,
                                                                         annotation=str))

            text = ref.resolved.content

        original_text = await commands.clean_content(escape_markdown=True).convert(ctx, text)

        if text is None:
            await ctx.send("Please enter text to be checked for grammar.")
            return

        embed = await self.grammar_correction(ctx.author, text)

        if isinstance(embed, tuple):
            self.bot.dispatch("command_error", ctx, embed[1], force=True, send_msg=False)
            return await ctx.send(f"Something went wrong. Try again later.")

        return await ctx.send(embed=embed)

    async def check_grammar_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        original_text = message.content

        if not original_text:
            return await interaction.response.send_message("No text found.")

        original_text = await commands.clean_content(escape_markdown=True).convert(
            await commands.Context.from_interaction(interaction), original_text
        )

        await interaction.response.defer(ephemeral=True, thinking=True)

        embed = await self.grammar_correction(interaction.user, original_text)

        if isinstance(embed, tuple):
            self.bot.tree.on_error(interaction, (embed[1], False))  # type: ignore
            return await interaction.followup.send(f"Something went wrong. Try again later.", ephemeral=True)

        return await interaction.response.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GrammarCorrection(bot))
