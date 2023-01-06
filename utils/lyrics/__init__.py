from dataclasses import asdict, dataclass, field

import discord
from discord.ext.commands import Paginator
from discord.ext.menus import ListPageSource as MenuSource

from core.music import LyricResult
from utils.paginator import YodaMenuPages


@dataclass(frozen=True, eq=True)
class PaginatedLyricResult:
    title: str = None
    artist: str = None
    lyrics: str = None
    paginated_lyrics: str = None
    images: dict[str, str] = field(default_factory=dict)


def paginate_lyric_result(res: LyricResult, limit: int = 4000):
    pag = Paginator(prefix="", suffix="", max_size=limit)

    for line in res.lyrics.split("\n"):
        pag.add_line(line)

    pages = []

    for page in pag.pages:
        pag_res = PaginatedLyricResult(**asdict(res), paginated_lyrics=page)

        pages.append(pag_res)

    return pages


class LyricsPaginator(MenuSource):
    def __init__(self, entries):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu: YodaMenuPages, res: PaginatedLyricResult):
        embed = discord.Embed(color=menu.ctx.bot.color)
        embed.title = res.title or "Title Unavailable."
        embed.description = res.paginated_lyrics
        embed.set_thumbnail(url=res.images.get("track"))
        embed.set_footer(text="Powered by Yoda API")

        if res.artist:
            embed.set_author(name=res.artist, icon_url=res.images.get("background"))

        return embed
