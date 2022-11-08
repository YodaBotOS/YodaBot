import asyncio
import importlib

import discord
from discord.ext import commands
from discord import app_commands

import config
from core import openai as core_openai
from utils.chat import *


class Chat(commands.Cog):
    """
    Chat with an AI
    """

    def __init__(self, bot: commands.Bot):
        self.openai = None
        self.bot = bot

    async def cog_load(self):
        importlib.reload(core_openai)
        from core.openai import OpenAI

        self.openai: OpenAI = OpenAI(config.OPENAI_KEY)

    async def cog_unload(self):
        del self.openai

    @commands.command('chat')
    @commands.max_concurrency(1, commands.BucketType.user)
    async def chat(self, ctx: commands.Context, *, text: str = None):
        """
        Chat with an AI
        """

        if text is not None:
            try:
                text = self.openai.chat(text)
            except Exception as e:
                return await ctx.send(f"Something went wrong, try again later.")

            embed = discord.Embed(color=self.bot.color)
            embed.set_author(name="Chat:", icon_url=ctx.author.display_avatar.url)
            embed.description = text

            return await ctx.send(embed=embed)

        view = ChatView(openai=self.openai, user=ctx.author, ephemeral=False)

        prev_msg = await ctx.send("YodaBot chat has started. Say `stop`, `goodbye`, `cancel`, `exit` or `end` to end "
                                  "the chat, or click the `Stop` button.", view=view)

        while not view.stopped:
            msg = await self.bot.wait_for('message',
                                          check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

            if view.stopped:
                return

            async with ctx.typing():
                text = msg.content

                if text.lower() in ['stop', 'goodbye', 'cancel', 'exit', 'end']:
                    view.stopped = True

                    for i in view.children:
                        i.disabled = True

                    await msg.edit(view=view)
                    return await ctx.send("Chat ended.")

                text = discord.utils.escape_markdown(text)

                # print(text)

                try:
                    text = self.openai.chat(text, user=ctx.author.id, channel=ctx.channel.id)
                except Exception as e:
                    print(e)
                    await ctx.send(f"Something went wrong. Try again later.", view=view)
                    continue

                embed = discord.Embed(color=self.bot.color)
                embed.set_author(name="Chat:", icon_url=ctx.author.display_avatar.url)
                embed.description = text

                if view.prev_msg and view.prev_msg.components:
                    await view.prev_msg.edit(view=None)
                await prev_msg.edit(view=None)

                prev_msg = await ctx.send(embed=embed, view=view)

    CHAT_SLASH_MAX_CONCURRENCY = commands.MaxConcurrency(1, per=commands.BucketType.user, wait=False)

    @app_commands.command(name='chat')
    async def chat_slash(self, interaction: discord.Interaction, text: str = None):
        """
        Chat with an AI
        """

        # As of right now, app_commands does not support max_concurrency, so we need to handle it ourselves in the
        # callback.
        ctx = await commands.Context.from_interaction(interaction)
        await self.CHAT_SLASH_MAX_CONCURRENCY.acquire(ctx.message)

        await interaction.response.defer()

        try:
            if text is not None:
                try:
                    text = self.openai.chat(text)
                except Exception as e:
                    return await interaction.followup.send(f"Something went wrong, try again later.", ephemeral=True)

                embed = discord.Embed(color=interaction.client.color)
                embed.set_author(name="Chat:", icon_url=interaction.user.display_avatar.url)
                embed.description = text

                return await interaction.followup.send(embed=embed)

            view = ChatView(openai=self.openai, user=ctx.author, ephemeral=True)

            await interaction.followup.send("YodaBot chat has started. click the `Stop` button to stop ",
                                            "chatting.", view=view)

            # For concurrency reasons, we gotta wait for the user to stop the chat until we can release it.
            await view.wait()
        finally:
            await self.CHAT_SLASH_MAX_CONCURRENCY.release(ctx.message)


async def setup(bot):
    await bot.add_cog(Chat(bot))
