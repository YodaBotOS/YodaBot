from __future__ import annotations

import re
import io
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
        embed.set_footer(text="Photo by: " + ", ".join(authors))

        return embed


class MapsView(ui.View):
    def __init__(self, maps: SlashMaps, place_id: str, photos: dict, landscape_aerial_view, portrait_aerial_view):
        self.maps = maps
        self.place_id = place_id
        self.photos = photos
        self.landscape_aerial_view = landscape_aerial_view
        self.portrait_aerial_view = portrait_aerial_view

        self.photos_cache = {}

        self.menu = self.generate_menu()

        super().__init__(timeout=None)

        if not all(self.landscape_aerial_view):
            self.remove_item(self.show_landscape)

        if not all(self.portrait_aerial_view):
            self.remove_item(self.show_portrait)

    def generate_menu(self):
        source = PhotosPaginator(self, self.photos)
        menu = YodaMenuPages(source)

        return menu

    @ui.button(label="Show Photos", emoji="\N{FRAME WITH PICTURE}", style=discord.ButtonStyle.blurple)
    async def show_photos(self, interaction: discord.Interaction, button: ui.Button):
        await self.menu.start(interaction)

    @ui.button(label="Show 3D Image (Portrait)", emoji="\N{CITYSCAPE}", style=discord.ButtonStyle.blurple)
    async def show_portrait(self, interaction: discord.Interaction, button: ui.Button):
        img, vid = self.portrait_aerial_view
        files = [discord.File(io.BytesIO(img), filename="portrait.png"), discord.File(io.BytesIO(vid), filename="portrait.mp4")]

        await interaction.response.send_message("3D Portrait Image and Video:", files=files, ephemeral=True)

    @ui.button(label="Show 3D Image (Landscape)", emoji="\N{CITYSCAPE}", style=discord.ButtonStyle.blurple)
    async def show_landscape(self, interaction: discord.Interaction, button: ui.Button):
        img, vid = self.landscape_aerial_view
        files = [discord.File(io.BytesIO(img), filename="landscape.png"), discord.File(io.BytesIO(vid), filename="landscape.mp4")]

        await interaction.response.send_message("3D Landscape Image and Video:", files=files, ephemeral=True)
