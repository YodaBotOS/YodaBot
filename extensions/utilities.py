from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING, Literal, Optional

import discord
import jishaku
from discord import app_commands
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
            yodabot_api_p = round(await self.bot.ping.api.yodabot(), 2)

            embed = discord.Embed(title="Ping/Latency:")

            if ctx.author.is_on_mobile():
                embed.add_field(name=f'{self.bot.ping.EMOJIS["bot"]} Bot (Websocket)', value=f"{bot_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["discord"]} Discord (API)', value=f"{discord_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["typing"]} Discord (Typing)', value=f"{typing_p}ms")
                embed.add_field(name=f'{self.bot.ping.EMOJIS["yodabot-api"]} API (YodaBot)', value=f"{yodabot_api_p}ms")
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

    @commands.hybrid_command(name=_T("source"))
    @app_commands.describe(command="The command to get the source code of.")
    async def source(self, ctx: Context, *, command: Optional[str] = None):
        """
        Get the source code of a command.
        """

        source_url = "https://github.com/Rapptz/RoboDanny"
        branch = "main"

        if command is None:
            return await ctx.send(source_url, embed_content=False)

        if command == "help":
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command)
            if obj is None:
                return await ctx.send("Could not find command.", embed_content=False, ephemeral=True)

            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)

        if module.startswith("discord"):
            location = module.replace(".", "/") + ".py"
            source_url = "https://github.com/Rapptz/discord.py"

            if discord.__version__.endswith(("a", "b", "rc")):
                branch = "master"
            else:
                branch = f"v{discord.__version__}"
        elif module.startswith("jishaku"):
            location = module.replace(".", "/") + ".py"
            source_url = "https://github.com/Gorialis/Jishaku"

            # Hacky way but idc
            with open("requirements.txt", "r") as fp:
                lines = [line.lower() for line in fp.readlines()]

                if (
                    "git+https://github.com/Gorialis/jishaku".lower() in lines
                    or "git+https://github.com/Gorialis/jishaku.git".lower() in lines
                ):
                    branch = "master"
                else:
                    branch = jishaku.__version__
        else:
            if filename is None:
                return await ctx.send("Could not find source for command.")

            location = os.path.relpath(filename).replace("\\", "/")

        final_url = f"<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>"

        return await ctx.send(final_url, embed_content=False)

    @source.autocomplete("command")
    async def source_command_autocomplete(self, interaction: discord.Interaction, current: str):
        if not current:
            return [
                app_commands.Choice(name=x.qualified_name, value=x.qualified_name) for x in self.bot.walk_commands()
            ][:25]

        _commands = self.bot.all_commands

        def add_commands_with_aliases(_commands, cmd):
            for sub in cmd.walk_commands():
                full_name = sub.full_parent_name + " " + sub.name
                _commands[full_name] = sub

                for alias in sub.aliases:
                    _commands[sub.full_parent_name + " " + alias] = sub

                if isinstance(sub, commands.Group):
                    add_commands_with_aliases(_commands, sub)

        for cmd in self.bot.commands:
            if isinstance(cmd, commands.Group):
                add_commands_with_aliases(_commands, cmd)

        keys = _commands.keys()

        match = []
        match2 = []

        if cmd := self.bot.get_command(current):
            match.append(cmd.qualified_name)

        for key in keys:
            if key.lower().startswith(current.lower()):
                match.append(key)
            if current.lower() in key.lower():
                match2.append(key)

        match += match2

        commands_match = {_commands[x] for x in match}

        return [app_commands.Choice(name=x.qualified_name, value=x.qualified_name) for x in commands_match][:25]

    @commands.hybrid_command("owner")
    async def owner(self, ctx: Context):
        """
        Displays the owner of this bot.
        """

        owner = await self.bot.application_info()

        if owner.team:
            owner = owner.team.owner
        else:
            owner = owner.owner

        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name="Owner", icon_url=self.bot.user.avatar.url)
        embed.description = f"I am powered by [YodaBot](https://github.com/YodaBotOS) organization, but my owner is {owner.mention} [`({owner}) - {owner.id}`](https://discord.com/users/{owner.id})"
        embed.set_thumbnail(url=owner.avatar.url)

        embed.set_footer(text="https://github.com/YodaBotOS")

        await ctx.send(embed=embed)

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
