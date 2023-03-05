from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.app_commands import locale_str as _T
from discord.ext import commands

from core.context import Context

if TYPE_CHECKING:
    from core.bot import Bot


class Utilities(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    @staticmethod
    def ansi(name, latency, spaces=18) -> str:
        if latency < 100:
            return f"\u001b[0;40;37m > \u001b[0;0m \u001b[0;34m{name}\u001b[0;0m {' ' * (spaces - len(name))} \u001b[0;1;37;40m : \u001b[0;0m \u001b[0;32m{latency}ms\u001b[0;0m"
        elif 100 <= latency < 250:
            return f"\u001b[0;40;37m > \u001b[0;0m \u001b[0;34m{name}\u001b[0;0m {' ' * (spaces - len(name))} \u001b[0;1;37;40m : \u001b[0;0m \u001b[0;33m{latency}ms\u001b[0;0m"
        elif latency >= 250:
            return f"\u001b[0;40;37m > \u001b[0;0m \u001b[0;34m{name}\u001b[0;0m {' ' * (spaces - len(name))} \u001b[0;1;37;40m : \u001b[0;0m \u001b[0;31m{latency}ms\u001b[0;0m"

    @commands.hybrid_command(name=_T("ping"), aliases=["latency"])
    async def ping(self, ctx: Context):
        """
        Get the bot's latency.
        """

        async with ctx.typing():
            bot_p = round(self.bot.ping.bot(), 2)
            discord_p = round(await self.bot.ping.discord(), 2)
            typing_p = round(await self.bot.ping.typing(), 2)
            r2_p = round(await self.bot.ping.r2(), 2)
            psql_p = round(await self.bot.ping.postgresql(), 2)
            # yodabot_api_p = round(await self.bot.ping.api.yodabot(), 2)

            embed = discord.Embed(title="Ping/Latency:")

            if ctx.author.is_on_mobile():
                embed.add_field(name=f'{self.bot.ping.EMOJIS["bot"]} Bot (Websocket)', value=f"{bot_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["discord"]} Discord (API)', value=f"{discord_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["typing"]} Discord (Typing)', value=f"{typing_p}ms")
                # embed.add_field(name=f'{self.bot.ping.EMOJIS["yodabot-api"]} API (YodaBot)', value=f"{yodabot_api_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["postgresql"]} Database', value=f"{psql_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["r2"]} CDN (R2)', value=f"{r2_p}ms")
            else:
                spaces = 18

                entries = []
                entries.append(self.ansi(f"Bot (Websocket)", bot_p, spaces))
                entries.append(self.ansi(f"Discord (API)", discord_p, spaces))
                entries.append(self.ansi(f"Discord (Typing)", typing_p, spaces))
                # entries.append(self.ansi(f"API (YodaBot)", yodabot_api_p, spaces))
                entries.append(self.ansi(f"Database", psql_p, spaces))
                entries.append(self.ansi(f"CDN (R2)", r2_p, spaces))

                embed.description = "```ansi\n"
                embed.description += "\n".join(entries)
                embed.description += "\n```"

            await ctx.send(embed=embed)

    @commands.hybrid_command(name=_T("uptime"))
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
