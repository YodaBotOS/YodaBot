from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord import ui
from discord.ext.menus import ListPageSource as MenuSource

from utils.paginator import YodaMenuPages

if TYPE_CHECKING:
    from core.maps import SlashMaps


class PhotosPaginator(MenuSource):
    def __init__(self, cls: "MapsView", entries):
        self.cls = cls
        super().__init__(entries, per_page=1)
        
    @staticmethod
    def parse_attributons(attributions):
        attr_regex = re.compile(r'<a href=".+">(?P<name>.+)</a>')
        
        l = []
        
        for attr in attributions:
            r = attr_regex.search(attr)
            l.append(r.group("name"))
            
        return l
        
    async def format_page(self, menu: YodaMenuPages, page: dict):
        if page["photo_reference"] in self.cls.photos_cache:
            image = self.cls.photos_cache[page["photo_reference"]]
        else:
            image = await self.cls.maps.get_photo(page["photo_reference"])
            self.cls.photos_cache[page["photo_reference"]] = image
        
        key = f"maps/{self.cls.place_id}/{page['photo_reference']}.png"
        menu.ctx.client.cdn.put_object(Body=image, Bucket="yodabot", Key=key)
        url = f"https://cdn.yodabot.xyz/{key}"
        
        authors = self.parse_attributons(page["html_attributions"])
        
        embed = discord.Embed(color=menu.ctx.client.color)
        embed.title = "Photos:"
        embed.set_image(url=url)
        embed.set_footer(text="Photo by: " + ', '.join(authors))
        
        return embed


class MapsView(ui.View):
    def __init__(self, maps: SlashMaps, place_id: str, photos: dict):
        self.maps = maps
        self.place_id = place_id
        self.photos = photos
        
        self.photos_cache = {}
        
        self.menu = self.generate_menu()
        
        super().__init__(timeout=None)
        
    def generate_menu(self):
        source = PhotosPaginator(self, self.photos)
        menu = YodaMenuPages(source)
        
        return menu
        
    @ui.button(label="Show Photos", emoji="\N{FRAME WITH PICTURE}", style=discord.ButtonStyle.blurple)
    async def show_photos(self, interaction: discord.Interaction, button: ui.Button):
        await self.menu.start(interaction)