import datetime
import typing
import uuid

import aiohttp
import cachetools
from discord import Interaction, app_commands
from discord.ext import commands
from yarl import URL

MAP_STYLES = typing.Literal["roadmap", "satellite", "terrain", "hybrid"]
MAP_THEMES = typing.Literal["standard", "light", "atlas", "dark", "dark-orange"]


class GoogleMapsAPI:
    LANGUAGE = "en"
    BASE_URL = URL("https://maps.googleapis.com/maps/api")
    FIND_PLACE_URL = BASE_URL / "place/findplacefromtext/json"
    AUTOCOMPLETE_URL = BASE_URL / "place/autocomplete/json"
    PLACE_DETAILS_URL = BASE_URL / "place/details/json"
    RENDER_MAPS_URL = BASE_URL / "staticmap"
    GET_PHOTO_URL = BASE_URL / "place/photo"
    AERIAL_VIEW = URL("https://aerialview.googleapis.com/v1beta/videos")

    MAP_IDS = {
        "standard": "23c821bf646d4f91",
        "light": "b1c242e5420989a",
        "atlas": "da6df2329e2c5290",
        "dark": "3ea09b97b8008fcc",
        "dark-orange": "aa5e322f8a9033f5",
    }

    ZOOM_LEVELS = {
        0: {"max-lng": 360.0, "max-lat": 170.0},
        1: {"max-lng": 360.0, "max-lat": 170.0},
        2: {"max-lng": 360.0, "max-lat": 170.0},
        3: {"max-lng": 360.0, "max-lat": 170.0},
        4: {"max-lng": 360.0, "max-lat": 170.0},
        5: {"max-lng": 180.0, "max-lat": 85.0},
        6: {"max-lng": 90.0, "max-lat": 42.5},
        7: {"max-lng": 45.0, "max-lat": 21.25},
        8: {"max-lng": 22.5, "max-lat": 10.625},
        9: {"max-lng": 11.25, "max-lat": 5.3125},
        10: {"max-lng": 5.625, "max-lat": 2.62625},
        11: {"max-lng": 2.8125, "max-lat": 1.328125},
        12: {"max-lng": 1.40625, "max-lat": 0.6640625},
        13: {"max-lng": 0.703125, "max-lat": 0.33203125},
        14: {"max-lng": 0.3515625, "max-lat": 0.166015625},
        15: {"max-lng": 0.17578125, "max-lat": 0.0830078125},
        16: {"max-lng": 0.087890625, "max-lat": 0.0415039063},
        17: {"max-lng": 0.0439453125, "max-lat": 0.0207519531},
        18: {"max-lng": 0.0219726563, "max-lat": 0.0103759766},
        19: {"max-lng": 0.0109863281, "max-lat": 0.0051879883},
        20: {"max-lng": 0.0054931641, "max-lat": 0.0025939941},
    }

    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session or aiohttp.ClientSession()

    def _get_params(self, keyword: str, data: dict, *, with_language: bool = True) -> dict:
        params = {
            "key": self.api_key,
        }

        if with_language:
            params["language"] = self.LANGUAGE

        params.update(data)

        return params

    async def find_place(self, query: str, *, fields: list[str] = None) -> list[dict]:
        params = self._get_params(
            "find_place",
            {
                "input": query,
                "inputtype": "textquery",
            },
        )

        if fields:
            params["fields"] = ",".join(fields)

        async with self.session.get(self.FIND_PLACE_URL, params=params) as resp:
            # https://developers.google.com/maps/documentation/places/web-service/search-find-place?hl=en_US#find-place-responses
            # https://developers.google.com/maps/documentation/places/web-service/search-find-place?hl=en_US#Place
            #
            js = await resp.json()

            return js["candidates"]

    async def autocomplete(self, query: str, *, text_only: bool = False, **kwargs) -> dict:
        params = {
            "input": query,
        }
        params.update(kwargs)
        params = self._get_params("autocomplete", params)

        async with self.session.get(self.AUTOCOMPLETE_URL, params=params) as resp:
            # https://developers.google.com/maps/documentation/places/web-service/autocomplete?hl=en_US#place_autocomplete_responses
            # https://developers.google.com/maps/documentation/places/web-service/autocomplete?hl=en_US#PlaceAutocompletePrediction
            js = await resp.json()

            if text_only:
                return [{"place": res["description"], "id": res["place_id"]} for res in js["predictions"]]

            return js["predictions"]

    async def place_details(self, place_id: str, *, fields: list[str] = None, **kwargs) -> dict:
        params = {
            "place_id": place_id,
        }
        params.update(kwargs)

        if fields:
            params["fields"] = ",".join(fields)

        params = self._get_params("place_details", params)

        async with self.session.get(self.PLACE_DETAILS_URL, params=params) as resp:
            # https://developers.google.com/maps/documentation/places/web-service/details?hl=en_US#PlaceDetailsResponses
            # https://developers.google.com/maps/documentation/places/web-service/details?hl=en_US#Place
            js = await resp.json()

            return js["result"]

    async def get_geometry(self, place_id: str) -> tuple[dict, dict]:
        place = await self.place_details(place_id, fields=["geometry"])

        return place["geometry"]["location"], place["geometry"]["viewport"]

    def get_zoom_level(self, viewport: dict) -> int:
        min_lat = min(viewport["northeast"]["lat"], viewport["southwest"]["lat"])
        max_lat = max(viewport["northeast"]["lat"], viewport["southwest"]["lat"])
        min_lng = min(viewport["northeast"]["lng"], viewport["southwest"]["lng"])
        max_lng = max(viewport["northeast"]["lng"], viewport["southwest"]["lng"])

        lat = max_lat - min_lat
        lng = max_lng - min_lng

        best_zoom = list(self.ZOOM_LEVELS.keys())[-1]

        for zoom, bounds in self.ZOOM_LEVELS.items():
            if zoom >= best_zoom:
                break

            if (
                bounds["max-lat"] >= lat > self.ZOOM_LEVELS[zoom + 1]["max-lat"]
                and lng <= bounds["max-lng"]
                and lng > self.ZOOM_LEVELS[zoom + 1]["max-lng"]
            ):
                best_zoom = zoom
                break

        if best_zoom > 2:
            best_zoom -= 2  # tbh idk why

        return best_zoom

    async def render(
        self,
        place_id: str,
        *,
        size: tuple[int, int] = (640, 640),
        map_type: MAP_STYLES = "roadmap",
        map_theme: MAP_THEMES = "standard",
        geometry: dict = None,
        **kwargs,
    ) -> bytes:
        if size[0] > 640 or size[1] > 640:
            raise ValueError("Size cannot be greater than 640x640")

        # Trying to minimize API calls as much as possible (cheaper)
        if geometry:
            loc = geometry["location"]
            vp = geometry["viewport"]
        else:
            loc, vp = await self.get_geometry(place_id)

        lat = loc["lat"]
        lng = loc["lng"]

        zoom = self.get_zoom_level(vp)

        params = {
            "center": f"{lat},{lng}",
            "markers": f"color:red|{lat},{lng}",
            "format": "png",
            "maptype": map_type,
            "zoom": zoom,
            "size": f"{size[0]}x{size[1]}",
            "map_id": self.MAP_IDS[map_theme],
        }
        params.update(kwargs)
        params = self._get_params("render", params)

        async with self.session.get(self.RENDER_MAPS_URL, params=params) as resp:
            return await resp.read()

    async def get_photo(self, photo_reference: str) -> bytes:
        params = self._get_params(
            "get_photo",
            {
                "photo_reference": photo_reference,
                "maxheight": 1600,
                "maxwidth": 1600,
            },
            with_language=False,
        )

        async with self.session.get(self.GET_PHOTO_URL, params=params) as resp:
            return await resp.read()

    async def aerial_view(
        self,
        address: str,
        orientation: typing.Literal["landscape", "portrait"],
        format: typing.Literal["image", "video"],
    ) -> bytes | None:
        params = self._get_params("aerial_view", {"address": address}, with_language=False)

        async with self.session.get(self.AERIAL_VIEW, params=params) as resp:
            js = await resp.json()

        if js.get("error", {}).get("status") == "NOT_FOUND":
            async with self.session.post(
                str(self.AERIAL_VIEW) + ":renderVideo",
                json={"address": address},
                params=self._get_params("aerial_view_post", {}, with_language=False),
            ) as resp:
                pass  # Let Google do the rest.

            return None
        elif js.get("state", "PROCESSING") == "PROCESSING" or js.get("state") != "ACTIVE":
            return None

        if "uris" not in js:
            # Something is going on, idk.
            return None

        if format == "image":
            g_url = js["uris"]["IMAGE"][f"{orientation}Uri"]
        elif format == "video":
            g_url = js["uris"]["MP4_MEDIUM"][f"{orientation}Uri"]

        async with self.session.get(g_url) as resp:
            return await resp.read()


# This is for slash commands (make things easier)
# It's to make things easier when using autocomplete and place_details together
# Google offers autocomplete and place_details in a bundle of a cheaper price, soooo
# We'll just use User ID as the session token with max_concurrency of 1 in the command
# Cause idk how else to share variables between autocomplete and slash commands
# And I'm lazy doing .author.id all the time in my code.
# This also makes it really flexible and customizable.
class SlashMaps:
    MAPS_INSTANCE: GoogleMapsAPI = None
    SESSION_TOKENS = cachetools.TLRUCache(
        maxsize=float("inf"),
        ttu=lambda _, __, now: now + datetime.timedelta(minutes=3),
        timer=datetime.datetime.utcnow,
    )

    def __init__(self, maps_instance: GoogleMapsAPI = None):
        if not maps_instance and not SlashMaps.MAPS_INSTANCE:
            raise ValueError("class has not been initiated yet")

        if maps_instance:
            SlashMaps.MAPS_INSTANCE = maps_instance

        self.maps_obj: GoogleMapsAPI = maps_instance or SlashMaps.MAPS_INSTANCE
        self.identifier: str = None

    @classmethod
    def initialize(cls, obj: commands.Context | Interaction) -> "SlashMaps":
        smaps = cls()

        if isinstance(obj, commands.Context):
            smaps.identifier = str(obj.author.id)
        elif isinstance(obj, Interaction):
            smaps.identifier = str(obj.user.id)
        else:
            raise TypeError("obj must be a Context or Interaction")

        return smaps

    def delete_session(self):
        try:
            del SlashMaps.SESSION_TOKENS[self.identifier]
        except KeyError:
            pass

    def get_session_token(self) -> str:
        session_token = self.SESSION_TOKENS.get(self.identifier)

        if not session_token:
            session_token = str(uuid.uuid4())

        self.SESSION_TOKENS[self.identifier] = session_token
        return session_token

    @property
    def session_token(self) -> str:
        return self.get_session_token()

    async def find_place(self, query: str, *, fields: list[str] = None) -> list[dict]:
        return await self.maps_obj.find_place(query, fields=fields)

    async def autocomplete(self, query: str, *, text_only: bool = False, **kwargs) -> list[dict]:
        return await self.maps_obj.autocomplete(query, text_only=text_only, sessiontoken=self.session_token, **kwargs)

    async def discord_slash_autocomplete(self, query: str, limit: int = None) -> list[app_commands.Choice]:
        place = await self.autocomplete(query, text_only=True)

        if limit is not None:
            place = place[:limit]

        choices = []

        for res in place:
            place_name = res["place"]

            if len(place_name) > 97:
                place_name = place_name[:97] + "..."

            choices.append(
                app_commands.Choice(name=place_name, value=res["id"])
            )  # returns place id (str) as the argument value

        return choices

    async def place_details(self, place_id: str, *, fields: list[str] = None, **kwargs) -> dict:
        return await self.maps_obj.place_details(place_id, fields=fields, sessiontoken=self.session_token, **kwargs)

    async def get_geometry(self, place_id: str) -> tuple[dict, dict]:
        return await self.maps_obj.get_geometry(place_id)

    def get_zoom_level(self, viewport: dict) -> int:
        return self.maps_obj.get_zoom_level(viewport)

    async def render(
        self,
        place_id: str,
        *,
        size: tuple[int, int] = (640, 640),
        map_type: MAP_STYLES = "roadmap",
        map_theme: MAP_THEMES = "standard",
        geometry: dict = None,
        **kwargs,
    ):
        return await self.maps_obj.render(
            place_id, size=size, map_type=map_type, map_theme=map_theme, geometry=geometry, **kwargs
        )

    async def get_photo(self, photo_reference: str) -> bytes:
        return await self.maps_obj.get_photo(photo_reference)

    async def aerial_view(
        self,
        address: str,
        orientation: typing.Literal["landscape", "portrait"],
        format: typing.Literal["image", "video"],
    ) -> bytes | None:
        return await self.maps_obj.aerial_view(address, orientation, format)
