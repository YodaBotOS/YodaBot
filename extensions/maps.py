from __future__ import annotations

import importlib
import io
import re
import typing
from typing import TYPE_CHECKING

import discord
import datetime
from discord import app_commands
from discord.ext import commands

from core import maps
from core.context import Context
from core.maps import SlashMaps
from utils.maps import MapsView

if TYPE_CHECKING:
    from core.bot import Bot


class Maps(commands.Cog):
    NECESSARY_FIELDS = [
        "business_status",
        "formatted_address",
        "geometry",
        "name",
        "photo",
        "url",
        "utc_offset",
        "international_phone_number",
        "opening_hours",
        "website",
        "rating",
    ]

    RATING_EMOJIS = {
        "full": "<:fullstar:1062375842564542495>",
        "half": "<:halfstar:1062375845169209405>",
        "empty": "<:emptystar:1062375839502708806>",
    }

    def __init__(self, bot: Bot):
        self.bot: Bot = bot

    async def cog_load(self):
        importlib.reload(maps)
        from core.maps import GoogleMapsAPI, SlashMaps

        SlashMaps(GoogleMapsAPI(self.bot.config.GCP_TOKEN, self.bot.session))

    async def place_autocomplete(self, interaction: discord.Interaction, current: str):
        maps = SlashMaps.initialize(interaction)

        return await maps.discord_slash_autocomplete(current, limit=25)

    def gen_stars(self, rating: int) -> str:
        s = ""

        for i in range(5):
            if rating >= 1:
                s += self.RATING_EMOJIS["full"]
                rating -= 1
            elif rating >= 0.5:
                s += self.RATING_EMOJIS["half"]
                rating -= 0.5
            else:
                s += self.RATING_EMOJIS["empty"]

        return s

    def format_embed(self, place: dict, embed: discord.Embed) -> discord.Embed:
        embed.title = place["name"]

        if website := place.get("website"):
            embed.url = website

        embed.description = ""

        if rating := place.get("rating"):
            embed.description += f"{self.gen_stars(rating)}\n\n"

        embed.description += place["formatted_address"]

        if phone := place.get("international_phone_number"):
            embed.description += f" - {phone}"

        if summary := place.get("editorial_summary"):
            embed.description += f'\n\n{summary["overview"]}'

        if business_status := place.get("business_status"):
            embed.add_field(
                name="Business Status:", value=f"`{business_status.lower().replace('_', ' ').title()}`", inline=False
            )

        timezone = None

        if utc_offset := place.get("utc_offset"):
            sign = "+"

            if utc_offset < 0:
                utc_offset = abs(utc_offset)
                sign = "-"

            thr = str(utc_offset // 60)
            tmin = str(utc_offset % 60)

            if thr == "0" and tmin == "0":
                timezone = "`UTC`"
            else:
                if thr == "0":
                    thr = "00"

                if tmin == "0":
                    tmin = "00"

                timezone = f"`UTC{sign}{thr}:{tmin}`"
                
            timezone_dt = datetime.timezone(datetime.timedelta(hours=int(thr), minutes=int(tmin)))
            
            timezone_now = datetime.datetime.now(timezone_dt)
            timezone_now_str = timezone_now.strftime(r"%A, %-d %B %Y - %-I:%M %p")

            embed.add_field(name="Timezone in that location:", value=f"{timezone}\n(Current time in that location is `{timezone_now_str}`)", inline=False)

        if opening_hours := place.get("opening_hours"):
            weekday_text = opening_hours["weekday_text"]

            regex1 = re.compile(
                r"(\w+): ([0-9]+):([0-9]+) (AM|PM) – ([0-9]+):([0-9]+) (AM|PM)"
            )  # some weird unicode characters google gave, idk why
            regex2 = re.compile(r"(\w+): (Closed)")

            replace1 = (
                lambda search: f"{search.group(1)}: `{search.group(2)}:{search.group(3)} {search.group(4)} – {search.group(5)}:{search.group(6)} {search.group(7)}`"
            )
            replace2 = lambda search: f"{search.group(1)}: `Closed`"

            def search(weekday_txt):
                if r := regex1.search(weekday_txt):
                    return replace1(r)
                elif r := regex2.search(weekday_txt):
                    return replace2(r)

            periods = []

            for day in weekday_text:
                periods.append(f"\N{BULLET} {search(day)}")

            periods = "\n".join(periods)

            embed.add_field(
                name="Opening Hours:",
                value=f"""
Open Now: `{opening_hours['open_now']}` 
Periods:
{periods}
            """
                + (f"\n(time is in {timezone})" if timezone else ""),
                inline=False,
            )

        embed.add_field(
            name="Geometry:",
            value=f"Latitude: `{place['geometry']['location']['lat']}`\n"
            f"Longitude: `{place['geometry']['location']['lng']}`\n"
            f"Coordinates: `{place['geometry']['location']['lat']}, {place['geometry']['location']['lng']}`",
            inline=False,
        )

        embed.set_footer(text=f"Powered by Google Maps", icon_url="https://cdn.yodabot.xyz/google-maps-icon.png")

        return embed

    MAX_CONCURRENCY = commands.MaxConcurrency(1, per=commands.BucketType.user, wait=False)

    async def handle(self, ctx, func, *args, **kwargs):
        if isinstance(ctx, discord.Interaction):
            ctx = await self.bot.get_context(ctx)

        try:
            await self.MAX_CONCURRENCY.acquire(ctx)
        except:
            return await ctx.send("You are already using this command!", ephemeral=True)

        try:
            await func(ctx, *args, **kwargs)
        finally:
            await self.MAX_CONCURRENCY.release(ctx)

    async def func(self, ctx, place_id, map_type, map_theme):
        maps = SlashMaps.initialize(ctx)

        place = await maps.place_details(
            place_id,
            language="en",
            fields=self.NECESSARY_FIELDS,
        )

        img = await maps.render(place_id, map_type=map_type, map_theme=map_theme, geometry=place["geometry"])
        f = discord.File(io.BytesIO(img), filename="map.png")

        maps.delete_session()

        embed = discord.Embed(color=self.bot.color)
        embed.set_image(url="attachment://map.png")

        embed = self.format_embed(place, embed)

        view = MapsView(maps, place_id, place["photos"])

        await ctx.send(embed=embed, view=view, file=f)

    async def send_autocomplete(self, maps, ctx, place):
        res = (await maps.autocomplete(place, text_only=True))[:25]

        options = []

        for place in res:
            place_name = place["place"]

            if len(place_name) > 97:
                place_name = place_name[:97] + "..."

            options.append(discord.SelectOption(label=place_name, value=place["id"]))

        class View(discord.ui.View):
            def __init__(self, cls):
                self.cls = cls
                self.place_id = None

                super().__init__(timeout=None)

            async def interaction_check(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not the author of this command!", ephemeral=True)
                    return False

                return True

            @discord.ui.select(placeholder="Select a place", options=options)
            async def select(self, interaction, select):
                await interaction.message.delete()

                self.place_id = select.values[0]

                self.stop()

        view = View(self)
        await ctx.send("Please select a place.", view=view, embed_content=False)
        await view.wait()

        return view.place_id

    @commands.command("maps", aliases=["map"])
    async def cmd(
        self,
        ctx: Context,
        map_type: typing.Optional[maps.MAP_STYLES] = "roadmap",
        map_theme: typing.Optional[maps.MAP_THEMES] = "standard",
        *,
        place: str,
    ):
        """
        Search for a place on Google Maps

        Place is the place you want to search for.

        Map Types can be either `roadmap`, `satellite`, `hybrid`, `terrain`. Defaults to `roadmap`.
        Map Themes can be either `standard`, `light`, `atlas`, `dark`, `dark-orange`. Defaults to `standard`.

        Usage: `yoda maps [map type] [map_theme] <place>`

        - `yoda maps Eiffel Tower`
        - `yoda maps satellite Great Wall of China`
        - `yoda maps terrain London`
        - `yoda maps hybrid dark-orange New York`
        - `yoda maps light Paris`
        """

        async def func(ctx, map_type, map_theme, place):
            maps = SlashMaps.initialize(ctx)

            place_id = await self.send_autocomplete(maps, ctx, place)

            return await self.func(ctx, place_id, map_type, map_theme)

        return await self.handle(ctx, func, map_type, map_theme, place)

    @app_commands.command(name="maps")
    @app_commands.describe(
        place="The place you want to search for",
        map_type="The map type to render the image as.",
        map_theme="The map theme to render the image as.",
    )
    @app_commands.autocomplete(place=place_autocomplete)
    async def slash_cmd(
        self,
        interaction: discord.Interaction,
        place: str,
        map_type: maps.MAP_STYLES = "roadmap",
        map_theme: maps.MAP_THEMES = "standard",
    ):
        """Search for a place on Google Maps"""

        async def func(ctx, place, map_type, map_theme):
            maps = SlashMaps.initialize(ctx)

            # Just to check if it's a valid place id or not (the user clicked one of the options or provided their own option).
            try:
                await maps.place_details(place, fields=["name"])
            except KeyError:
                place = await self.send_autocomplete(maps, ctx, place)

            return await self.func(ctx, place, map_type, map_theme)

        return await self.handle(interaction, func, place, map_type, map_theme)


async def setup(bot):
    await bot.add_cog(Maps(bot))
