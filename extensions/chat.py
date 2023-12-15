from __future__ import annotations

import asyncio
import importlib
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands

import config
from core import openai as core_openai
from core.context import Context
from utils.chat import *

if TYPE_CHECKING:
    from core.bot import Bot


class Chat(commands.Cog):
    """
    Chat with an AI
    """

    def __init__(self, bot: Bot):
        self.openai = None
        self.bot: Bot = bot

    async def cog_load(self):
        importlib.reload(core_openai)
        from core.openai import OpenAI

        self.openai: OpenAI = OpenAI(config.OPENAI_KEY, bot=self.bot)
        self.bot.openai = self.openai
        self.google = self.openai.googlechat(config.SERPAPI)

    async def cog_unload(self):
        del self.openai

    CHAT_SLASH_MAX_CONCURRENCY = commands.MaxConcurrency(1, per=commands.BucketType.member, wait=False)

    @commands.command("chat", aliases=["assistant"])
    # @commands.max_concurrency(1, commands.BucketType.member)
    async def chat(self, ctx: Context, *, text: str = None):
        """
        Chat with an AI using the latest GPT-4 OpenAI Model.
        """

        await self.CHAT_SLASH_MAX_CONCURRENCY.acquire(ctx.message)

        try:
            if text is not None:
                async with ctx.typing():
                    try:
                        text = await self.openai.chat(ctx, text)
                    except Exception as e:
                        await ctx.send(f"Something went wrong, try again later.")
                        self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)
                        return

                    embed = discord.Embed(color=self.bot.color)
                    embed.set_author(name="Chat:", icon_url=ctx.author.display_avatar.url)
                    embed.add_field(name="Input/Prompt:", value=text_prompt, inline=False)
                    embed.add_field(name="Output/Response:", value=text, inline=False)
                    embed.set_footer(
                        text=f"Powered by OpenAI GPT-4.\n\U000026a0: This is on beta and may not be accurate and can spread biases, etc."
                    )

                    return await ctx.send(embed=embed)

            await self.openai.chat.new(ctx, "assistant")
            view = ChatView(openai=self.openai.chat, user=ctx.author, ephemeral=False)

            prev_msg = await ctx.send(
                "YodaBot chat has started. Say `stop`, `goodbye`, `cancel`, `exit` or `end` to end "
                "the chat, or click the `Stop` button.",
                view=view,
            )

            while not view.stopped:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                )

                if view.stopped:
                    return

                async with ctx.typing():
                    text = msg.content.strip()

                    if text.lower() in ["stop", "goodbye", "cancel", "exit", "end"]:
                        view.stopped = True

                        for i in view.children:
                            i.disabled = True

                        await msg.edit(view=view)
                        return await ctx.send("Chat ended.")

                    text_prompt = discord.utils.escape_markdown(text)

                    # print(text)

                    try:
                        text = await self.openai.chat.reply(ctx, text_prompt, msg)
                    except Exception as e:
                        await ctx.send(f"Something went wrong. Try again later.", view=view)
                        self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)
                        return

                    embed = discord.Embed(color=self.bot.color)
                    embed.set_author(name="Chat:", icon_url=ctx.author.display_avatar.url)
                    embed.add_field(name="Input/Prompt:", value=text_prompt, inline=False)
                    embed.add_field(name="Output/Response:", value=text, inline=False)
                    embed.set_footer(
                        text=f"Powered by OpenAI GPT-4.\n\U000026a0: This is on beta and may not be accurate and can spread biases, etc."
                    )

                    if view.prev_msg and view.prev_msg.components:
                        await view.prev_msg.edit(view=None)
                    await prev_msg.edit(view=None)

                    prev_msg = await ctx.send(embed=embed, view=view)
        finally:
            await self.CHAT_SLASH_MAX_CONCURRENCY.release(ctx.message)

    @app_commands.command(name=_T("chat"))
    @app_commands.describe(text="The text to chat with the AI (once)", role="The role you want the chatbot to be")
    async def chat_slash(self, interaction: discord.Interaction, text: str = None, role: str = "assistant"):
        """
        Chat with an AI using the new GPT-4 OpenAI Model.
        """

        # As of right now, app_commands does not support max_concurrency, so we need to handle it ourselves in the
        # callback.
        ctx = await Context.from_interaction(interaction)
        await self.CHAT_SLASH_MAX_CONCURRENCY.acquire(ctx.message)

        await interaction.response.defer()

        try:
            if text is not None:
                try:
                    text = await self.openai.chat(interaction, text, role=role)
                except Exception as e:
                    await interaction.followup.send(f"Something went wrong, try again later.", ephemeral=True)
                    await self.bot.tree.on_error(interaction, (e, False))

                embed = discord.Embed(color=interaction.client.color)
                embed.set_author(name="Chat:", icon_url=interaction.user.display_avatar.url)
                embed.description = text

                return await interaction.followup.send(embed=embed)

            await self.openai.chat.new(ctx, role)
            view = ChatView(openai=self.openai.chat, user=ctx.author, ephemeral=True)

            await interaction.followup.send(
                "YodaBot chat has started. click the `Stop` button to stop chatting.",
                view=view,
            )

            # For concurrency reasons, we gotta wait for the user to stop the chat until we can release it.
            await view.wait()
        finally:
            await self.CHAT_SLASH_MAX_CONCURRENCY.release(ctx.message)

    @chat_slash.autocomplete("role")
    async def chat_slash_autocomplete(self, interaction: discord.Interaction, role: str):
        roles = [x.title() for x in self.openai.chat.CHAT_ROLES.keys()]

        results = [x for x in roles if x.lower().startswith(role.lower()) or role.lower() in x.lower()][:25]

        results = results or roles[:25]

        return [app_commands.Choice(name=x, value=x) for x in results]

    @commands.command(
        "googlegpt", aliases=["googlechat", "bard", "google-gpt", "google_gpt", "google-chat", "google_chat", "gg"]
    )
    async def google_gpt(self, ctx: Context, *, text: str = None):
        """
        OpenAI GPT-4 x Google Search. ON BETA!!
        """

        await self.CHAT_SLASH_MAX_CONCURRENCY.acquire(ctx.message)

        try:
            if text is not None:
                async with ctx.typing():
                    try:
                        text = await self.google(ctx, text)
                    except Exception as e:
                        await ctx.send(f"Something went wrong, try again later.")
                        self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)
                        return

                    embed = discord.Embed(color=self.bot.color)
                    embed.set_author(name="GoogleGPT Chat:", icon_url=ctx.author.display_avatar.url)
                    embed.add_field(name="Input/Prompt:", value=text_prompt, inline=False)
                    embed.add_field(name="Output/Response:", value=text, inline=False)
                    embed.set_footer(
                        text=f"Powered by OpenAI GPT-4 x Google Search.\n\U000026a0: This is on beta and may not be accurate and can spread biases, etc."
                    )

                    return await ctx.send(embed=embed)

            await self.google.new(ctx)
            view = ChatView(openai=self.google, user=ctx.author, ephemeral=False, google=True)

            prev_msg = await ctx.send(
                "YodaBot GoogleGPT chat has started. Say `stop`, `goodbye`, `cancel`, `exit` or `end` to end "
                "the chat, or click the `Stop` button.",
                view=view,
            )

            while not view.stopped:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                )

                if view.stopped:
                    return

                async with ctx.typing():
                    text = msg.content.strip()

                    if text.lower() in ["stop", "goodbye", "cancel", "exit", "end"]:
                        view.stopped = True

                        for i in view.children:
                            i.disabled = True

                        await msg.edit(view=view)
                        return await ctx.send("Chat ended.")

                    text_prompt = discord.utils.escape_markdown(text)

                    # print(text)

                    try:
                        text = await self.google.reply(ctx, text_prompt)
                    except Exception as e:
                        await ctx.send(f"Something went wrong. Try again later.", view=view)
                        self.bot.dispatch("command_error", ctx, e, force=True, send_msg=False)
                        return

                    embed = discord.Embed(color=self.bot.color)
                    embed.set_author(name="GoogleGPT Chat:", icon_url=ctx.author.display_avatar.url)
                    embed.add_field(name="Input/Prompt:", value=text_prompt, inline=False)
                    embed.add_field(name="Output/Response:", value=text, inline=False)
                    embed.set_footer(
                        text=f"Powered by OpenAI GPT-4 x Google Search.\n\U000026a0: This is on beta and may not be accurate and can spread biases, etc."
                    )

                    if view.prev_msg and view.prev_msg.components:
                        await view.prev_msg.edit(view=None)
                    await prev_msg.edit(view=None)

                    prev_msg = await ctx.send(embed=embed, view=view)
        finally:
            await self.CHAT_SLASH_MAX_CONCURRENCY.release(ctx.message)

    @app_commands.command(name="google-gpt")
    @app_commands.describe(text="The text to chat with the AI (once)")
    async def google_gpt_slash(self, interaction: discord.Interaction, text: str = None):
        """
        OpenAI GPT-4 x Google Search. ON BETA!!
        """

        # As of right now, app_commands does not support max_concurrency, so we need to handle it ourselves in the
        # callback.
        ctx = await Context.from_interaction(interaction)
        await self.CHAT_SLASH_MAX_CONCURRENCY.acquire(ctx.message)

        await interaction.response.defer()

        try:
            if text is not None:
                try:
                    text = await self.google(interaction, text)
                except Exception as e:
                    await interaction.followup.send(f"Something went wrong, try again later.", ephemeral=True)
                    await self.bot.tree.on_error(interaction, (e, False))

                embed = discord.Embed(color=interaction.client.color)
                embed.set_author(name="GoogleGPT Chat:", icon_url=interaction.user.display_avatar.url)
                embed.description = text

                return await interaction.followup.send(embed=embed)

            await self.google.new(ctx)
            view = ChatView(openai=self.google, user=ctx.author, ephemeral=True, google=True)

            await interaction.followup.send(
                "YodaBot GoogleGPT chat has started. click the `Stop` button to stop chatting.",
                view=view,
            )

            # For concurrency reasons, we gotta wait for the user to stop the chat until we can release it.
            await view.wait()
        finally:
            await self.CHAT_SLASH_MAX_CONCURRENCY.release(ctx.message)


async def setup(bot):
    await bot.add_cog(Chat(bot))
