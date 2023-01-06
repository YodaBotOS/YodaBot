from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Bot


class Context(commands.Context):
    """
    YodaBot's Custom Context
    """

    bot: Bot

    async def send(
        self,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        embeds: Optional[Sequence[discord.Embed]] = None,
        **kwargs,
    ):
        if (
            self.command.root_parent != self.bot.get_command("jishaku")
            and kwargs.pop("embed_content", True)
            and not embed
            and not embeds
        ):
            embed = discord.Embed(description=content, color=self.bot.color)
            content = None

        return await super().send(content, embed=embed, embeds=embeds, **kwargs)
