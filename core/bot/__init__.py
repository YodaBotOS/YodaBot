from __future__ import annotations

import datetime
import json
import os
import typing
from typing import TYPE_CHECKING

import aiohttp
import asyncpg
import boto3
import discord
import mystbin
import sentry_sdk
import wavelink
from discord import app_commands
from discord.ext import commands
from rich.traceback import install as install_rich_traceback

import config as cfg
from core.context import Context
from core.openai import OpenAI
from core.ping import Ping
from utils.app_commands import CommandTree
from utils.translator import Translator

# from wavelink.ext import spotify


if TYPE_CHECKING:
    from mypy_boto3_s3 import Client as S3Client

install_rich_traceback()


EXTENSIONS = [
    "extensions.ocr",
    "extensions.translate",
    "extensions.text",
    "extensions.chat",
    "extensions.image",
    "extensions.study_notes",
    "extensions.music",
    "extensions.utilities",
    "extensions.maps",
    "extensions.code",
]


class Bot(commands.Bot):
    """
    YodaBot
    """

    connected: bool
    main_prefix: str | list[str]
    is_selfhosted: bool
    config: cfg
    uptime: datetime.datetime
    color: discord.Colour
    session: aiohttp.ClientSession
    mystbin: mystbin.Client
    openai: OpenAI
    cdn: S3Client
    pool: asyncpg.Pool
    ping: Ping

    def __init__(self, command_prefix: typing.Any = None, *args, **kwargs):
        self.connected = False
        self.main_prefix = cfg.PREFIX if isinstance(cfg.PREFIX, str) else cfg.PREFIX[0]
        self.is_selfhosted = os.environ.get("IS_SELFHOST", "1") == "1"
        self.token = kwargs.pop("token", None) or cfg.TOKEN

        command_prefix = command_prefix or commands.when_mentioned_or(*list(cfg.PREFIX))
        intents: discord.Intents = kwargs.pop("intents", None) or discord.Intents.all()
        description: str = kwargs.pop("description", None) or cfg.DESCRIPTION
        activity: discord.Activity = (
            kwargs.pop("activity", None)
            or discord.Activity(
                type=discord.ActivityType.listening, name=f'"{self.main_prefix}help"'
            )
            if not self.is_selfhosted
            else None
        )
        help_command: commands.HelpCommand = (
            kwargs.pop("help_command", None) or commands.MinimalHelpCommand()
        )
        strip_after_prefix: bool = kwargs.pop("strip_after_prefix", None) or True
        tree_cls: app_commands.CommandTree = kwargs.pop("tree_cls", None) or CommandTree
        case_insensitive: bool = kwargs.pop("case_insensitive", True)

        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            description=description,
            activity=activity,
            help_command=help_command,
            strip_after_prefix=strip_after_prefix,
            tree_cls=tree_cls,
            case_insensitive=case_insensitive,
            **kwargs,
        )

    async def get_context(
        self,
        message: discord.Message | discord.Interaction,
        *,
        cls: commands.Context = None,
    ) -> Context:
        return await super().get_context(message, cls=cls or Context)

    async def setup_hook(self) -> None:
        self.uptime = discord.utils.utcnow()
        self.color = discord.Colour(cfg.COLOR)  # C5D8FE
        self.session = aiohttp.ClientSession()
        self.mystbin = mystbin.Client(session=self.session)

        self.config = cfg

        if google_credentials_path := getattr(
            cfg, "GOOGLE_APPLICATION_CREDENTIALS_PATH", None
        ):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_credentials_path

        os.environ["OPENAI_API_KEY"] = cfg.OPENAI_KEY
        self.openai = OpenAI(cfg.OPENAI_KEY)

        # Jishaku Environment Vars
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

        # R2/S3/boto3 CDN
        self.cdn = boto3.client(
            "s3",
            endpoint_url=cfg.CDN_ENDPOINT_URL,
            aws_access_key_id=cfg.CDN_ACCESS_KEY,
            aws_secret_access_key=cfg.CDN_SECRET_KEY,
        )
        
        self.pool: asyncpg.Pool = await asyncpg.create_pool(cfg.POSTGRESQL_DSN)

        # await self.pool.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
        
        with open("schema.sql") as f:
            await self.pool.execute(f.read())

        self.ping = Ping(self)

        # print("Setting up translator")
        # await self.tree.set_translator(Translator(self))

        # TODO: Wavelink
        # nodes = []

        # for n in cfg.WAVELINK_NODES:
        #     nodes.append(wavelink.Node(uri=n['uri'], password=n['password'], session=self.session))

        # await wavelink.NodePool.connect(client=self, nodes=nodes, spotify=spotify.SpotifyClient(client_id=cfg.SPOTIFY_CLIENT_ID, client_secret=cfg.SPOTIFY_CLIENT_SECRET))

        # Load cogs
        exts = EXTENSIONS.copy()
        exts.extend(["jishaku", "extensions.events"])
        for extension in exts:
            await self.load_extension(extension)
            print("Loaded extension:", extension)

        if not self.is_selfhosted:
            sentry_sdk.init(cfg.SENTRY_DSN, traces_sample_rate=1.0)

    def run(self, token: str = None, *args, **kwargs) -> None:
        token = token or self.token
        super().run(token, *args, **kwargs)
