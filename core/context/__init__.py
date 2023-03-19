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
        embed_content: Optional[bool] = True,
        **kwargs,
    ):
        root_parent = self.command.root_parent if self.command else None
        if root_parent != self.bot.get_command("jishaku") and embed_content and not embed and not embeds:
            embed = discord.Embed(description=content, color=self.bot.color)
            content = None

        if embed and not embed.color:
            embed.color = self.bot.color

        if embeds:
            for embed in embeds:
                if not embed.color:
                    embed.color = self.bot.color

        return await super().send(content, embed=embed, embeds=embeds, **kwargs)
