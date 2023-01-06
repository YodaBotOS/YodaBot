from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.ext import commands

from core.context import Context

if TYPE_CHECKING:
    from core.bot import Bot


class Utilities(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @commands.hybrid_command(aliases=["latency"])
    async def ping(self, ctx: Context):
        """
        Get the bot's latency.
        """

        return await ctx.send(f"Pong! `{round(self.bot.latency * 1000, 2)}ms`")

    @commands.hybrid_command()
    async def uptime(self, ctx: Context):
        """
        Get the bot's uptime.
        """

        return await ctx.send(
            f"The bot was last restarted {discord.utils.format_dt(self.bot.uptime, 'R')} ago ({discord.utils.format_dt(self.bot.uptime, 'F')})."
        )

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ):
        """
        !sync -> Global sync
        !sync ~ -> Sync current guild
        !sync \* -> Copies all global app commands to current guild and syncs
        !sync ^ -> Clears all commands from the current guild target and syncs (removes guild commands)
        !sync id_1 id_2 -> Syncs guilds with id 1 and 2
        """

        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot):
    await bot.add_cog(Utilities(bot))
