from __future__ import annotations

import re
import sys
import traceback
from typing import TYPE_CHECKING

import discord
import sentry_sdk
from discord.ext import commands

from core.context import Context

if TYPE_CHECKING:
    from core.bot import Bot


class Events(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.connected:
            self.bot.connected = True
            print(f"Bot ({self.bot.user} with ID {self.bot.user.id}) is ready and online!")
            print(f'Prefix is: "{self.bot.main_prefix}"')
        else:
            print("Bot reconnected!")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return

        if self.bot.is_selfhosted and not await self.bot.is_owner(msg.author):
            return

        if not self.bot.is_selfhosted:
            if re.fullmatch(rf"<@!?{self.bot.user.id}>", msg.content):
                return await msg.channel.send(f"My prefix is `{self.bot.main_prefix}`! You can also mention me!")

    @commands.Cog.listener()
    async def on_message_edit(self, b, a):
        if b.content == a.content:
            return

        return await self.bot.process_commands(a)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception, *, force: bool = False, send_msg: bool = True):
        ignored = (commands.CommandNotFound,)

        if not force:
            if ctx.command and ctx.command.has_error_handler():
                return

            if ctx.cog and ctx.cog.has_error_handler():
                return

        if isinstance(error, ignored):
            print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
            traceback.print_exception(error)
            return

        try:
            if send_msg:
                await ctx.send(f"Error: {error}")
        except:
            pass

        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        traceback.print_exception(error)

        with sentry_sdk.push_scope() as scope:
            scope.set_user({"username": str(ctx.author), "id": ctx.author.id})
            scope.set_tag("command-type", "message")
            scope.set_extra("command", str(ctx.command))

            sentry_sdk.capture_exception(error, scope=scope)


async def setup(bot):
    await bot.add_cog(Events(bot))
