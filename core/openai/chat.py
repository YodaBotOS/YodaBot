from __future__ import annotations

import datetime
import json
import typing

import discord

from core.context import Context
from core.serp import SerpAPI

if typing.TYPE_CHECKING:
    from . import OpenAI

import openai


class ChatBase:  # Base class for Chat and GoogleChat
    TTL = datetime.timedelta(minutes=3)

    MODEL = "gpt-4"

    def __init__(self, openai_cls: OpenAI):
        self.openai = openai_cls
        self.bot = openai_cls.bot

        openai.api_key = self.openai.key
        self.client = self.openai.client

    # Backend functions
    async def _get(self, user_id: int, channel_id: int, *, conn=None) -> dict | None:
        if conn:
            row = await conn.fetchrow(
                "SELECT * FROM chat WHERE user_id=$1 AND channel_id=$2",
                user_id,
                channel_id,
            )
        else:
            row = await self.bot.pool.fetchrow(
                "SELECT * FROM chat WHERE user_id=$1 AND channel_id=$2",
                user_id,
                channel_id,
            )

        if row is not None:
            return dict(row)

    async def _check_class(
        self, user_id: int, channel_id: int, is_google: bool | None = None, *, conn=None
    ) -> bool:
        is_google = (
            is_google
            if is_google is not None
            else self.__class__.__name__ == "GoogleChat"
        )

        r = await self._get(user_id, channel_id, conn=conn)
        return r.get("is_google") == is_google

    async def _perf_db(
        self,
        user_id: int,
        channel_id: int,
        messages: list[dict[str, str]],
        *,
        is_google: bool | None = None,
    ):
        x = await self._get(user_id, channel_id)

        if x and x["ttl"] < discord.utils.utcnow():
            try:
                await self._delete(user_id, channel_id)
            except:
                pass

            x = None

        is_google = (
            is_google
            if is_google is not None
            else self.__class__.__name__ == "GoogleChat"
        )

        async with self.bot.pool.acquire() as conn:
            await conn.set_type_codec(
                "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
            )

            if not x:
                await conn.execute(
                    "INSERT INTO chat (user_id, channel_id, messages, ttl, is_google) VALUES ($1, $2, $3::json, $4, $5)",
                    user_id,
                    channel_id,
                    messages,
                    discord.utils.utcnow() + self.TTL,
                    is_google,
                )
            else:
                check = await self._check_class(
                    user_id, channel_id, is_google, conn=conn
                )
                if not check:
                    raise ValueError(
                        "Chat session is supposed to be Google Chat but it's not or vice versa."
                    )

                await conn.execute(
                    "UPDATE chat SET messages=$3::json, ttl=$4 WHERE user_id=$1 AND channel_id=$2",
                    user_id,
                    channel_id,
                    messages,
                    discord.utils.utcnow() + self.TTL,
                )

    async def _delete(self, user_id: int, channel_id: int):
        await self.bot.pool.execute(
            "DELETE FROM chat WHERE user_id=$1 AND channel_id=$2", user_id, channel_id
        )

    def _init_messages(self, *, system: str | None = None) -> list[dict[str, str]]:
        system = getattr(super, "SYSTEM", None)

        if system is None:
            return []

        return [{"role": "system", "content": system}]

    # Chat methods
    async def get(self, context: Context | discord.Interaction) -> dict | None:
        if isinstance(context, Context):
            return await self._get(context.author.id, context.channel.id)
        else:
            return await self._get(context.user.id, context.channel.id)

    async def perf_db(
        self, context: Context | discord.Interaction, messages: list[dict[str, str]]
    ) -> None:
        if isinstance(context, Context):
            await self._perf_db(context.author.id, context.channel.id, messages)
        else:
            await self._perf_db(context.user.id, context.channel.id, messages)

    async def new(self, context: Context | discord.Interaction) -> None:
        try:
            await self.stop(context)
        except:
            pass

        messages = self._init_messages()
        await self.perf_db(context, messages)

    async def stop(self, context: Context | discord.Interaction) -> None:
        data = await self.get(context)

        if data is None:
            raise ValueError("Chat session not found. Might have already been deleted.")

        if isinstance(context, Context):
            await self._delete(context.author.id, context.channel.id)
        else:
            await self._delete(context.user.id, context.channel.id)

    async def reply(self, *args, **kwargs):
        raise NotImplementedError

    async def __call__(self, context: Context | discord.Interaction, message: str):
        await self.new(context)
        x = await self.reply(context, message)
        await self.stop(context)

        return x


class GoogleChat(ChatBase):  # GoogleGPT
    SYSTEM = """You are an AI that can help on searching things on Google and summarizing the result to the user. 
User will say something like "Who is the current president of the United States", you should call the search google function with only the term, e.g (search_google("Current President of the United States"))
Another short example is "What is Starbucks?", because "Starbucks" (taken from term) is a general topic, you should call the search google function with the complete content, e.g (search_google("What is Starbucks?"))
Another example is "What is the capital of France", you should call the search google function with only the term, e.g (search_google("Capital of France"))
Another example is "Where is the Eifel Tower located?", you should call the search google function with only the term, e.g (search_google("Location of Eifel Tower")).
Another example is "What is the weather forcast for Los Angeles tommorrow?", you should call the search google function with only the term, e.g (search_google("Weather forcast for Los Angeles tommorrow")).
Another example is "What time is it right now in London?", you should call the search google function with only the term, e.g (search_google("Time in London")).

This is limited to: 
- Getting nearby/local results that involves the current location, e.g asking for the nearest coffee shop or mcdonald's should not work and should be responded with "I can't help you with local results. I don't know where you are." or somehting like this unless provided with a specific location e.g "What's the weather forcast for Los Angeles tommorrow?" or "What time is it right now in NYC?".
"""  # - Getting references/citations for a result, e.g asking for the references of the last result. This should not work and should be responded with "I can't help you with references/citations. I don't know how to do that." or something like this.

    FUNCTIONS = [
        {
            "name": "search_google",
            "description": "Searches Google for the given term and returns the result for real-time data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "The term/query to search for in Google.",
                    }
                },
                "required": ["term"],
            },
        }
    ]

    def __init__(self, serp_api_key: str, openai_cls: OpenAI):
        super().__init__(openai_cls)

        self.serp_api_key = serp_api_key
        self.serp = SerpAPI(self.serp_api_key, session=self.bot.session)

    # Chat methods
    async def get(
        self, context: Context | discord.Interaction, *, is_google: bool = False
    ) -> dict | None:
        results = super().get(context)
        if (
            results and is_google and results.get("is_google") == is_google
        ):  # if is_google is True, it's forced to be google chat. If it's False, it's not forced to be google chat (can be normal chat).
            return results

    async def reply(self, context: Context | discord.Interaction, message: str) -> str:
        data = await self.get(context)

        if data is None:
            raise ValueError("Chat session not found. Create one by doing `.new(...)`")

        if data["ttl"] < discord.utils.utcnow():
            try:
                await self.stop(context)
            except:
                pass

            return

        messages = data["messages"]

        messages.append({"role": "user", "content": message})

        if isinstance(context, Context):
            user = context.author.id
        else:
            user = context.user.id

        resp = await self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            user=str(user),
            tools=self.FUNCTIONS,
            tool_choice="auto",
        )

        response = resp.choices[0].message

        if tool_calls := response.tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                assert (
                    function_name == "search_google"
                ), f"Unknown function name: {function_name}"

                fuction_to_call = self.serp.google_search
                function_args = json.loads(tool_call.function.arguments)
                function_response = await fuction_to_call(
                    query=function_args.get("term"),
                )

                function_response.pop("query")
                function_response.pop("images")
                function_content = json.dumps(function_content)

                messages.append(response)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_content,
                    }
                )
                second_resp = await self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                )

                response = second_resp.choices[0].message

        messages.append({"role": response.role, "content": response.content})

        await self.perf_db(context, messages)

        return response.content


class Chat(ChatBase):  # GPT
    DID_NOT_UNDERSTAND = "Sorry, I didn't understand what you meant."

    CHAT_ROLES = {}  # Taken from https://github.com/f/awesome-chatgpt-prompts#prompts

    MODEL = "gpt-4-vision-preview"

    def __init__(self, openai_cls: OpenAI):
        super().__init__(openai_cls)
        self._init_chat_roles()

    # Backend functions
    def _init_chat_roles(self):
        with open("core/openai/chat-roles.json") as f:
            self.CHAT_ROLES = json.load(f)

    def _init_messages(
        self, context: Context | discord.Interaction, role: str
    ) -> list[dict[str, str]]:
        # Where all the personalization for the chatbot goes such as who are you, what server/channel you are in, etc.
        role = role.lower()

        if isinstance(context, Context):
            personalize = f"Your name is YodaBot and you are chatting with a person with the username {context.author} with the user id {context.author.id} in the server {context.guild} with the server id {context.guild.id} in the channel {context.channel} with the channel id {context.channel.id}."
        else:
            personalize = f"Your name is YodaBot and you are chatting with a person with the username {context.user} with the user id {context.user.id} in the server {context.guild} with the server id {context.guild.id} in the channel {context.channel} with the channel id {context.channel.id}."

        system = self.CHAT_ROLES.get(role, role) + "\n\n" + personalize

        return super()._init_messages(system=system)

    # Chat methods
    async def new(self, context: Context | discord.Interaction, role: str) -> None:
        try:
            await self.stop(context)
        except:
            pass

        messages = self._init_messages(context, role)
        await self.perf_db(context, messages)

    async def reply(
        self,
        context: Context | discord.Interaction,
        message: str,
        msg: discord.Message = None,
    ) -> str:
        data = await self.get(context)

        if data is None:
            raise ValueError("Chat session not found. Create one by doing `.new(...)`")

        if data["ttl"] < discord.utils.utcnow():
            try:
                await self.stop(context)
            except:
                pass

            return

        messages = data["messages"]
        content = [{"type": "text", "text": message}]
        if msg and (attachments := msg.attachments):
            for attach in attachments:
                if attach.content_type in [
                    "image/png",
                    "image/jpg",
                    "image/jpeg",
                    "image/webp",
                    "image/gif",
                ]:
                    content.append({"type": "image", "image_url": {"url": attach.url}})

        messages.append({"role": "user", "content": content})

        if isinstance(context, Context):
            user = context.author.id
        else:
            user = context.user.id

        resp = await self.client.chat.completions.create(
            model=self.MODEL, messages=messages, user=str(user), max_tokens=4096
        )

        response = resp.choices[0].message

        if not response.content:
            response = self.DID_NOT_UNDERSTAND

        messages.append({"role": response.role, "content": response.content})

        await self.perf_db(context, messages)

        return response.content

    async def __call__(
        self,
        context: Context | discord.Interaction,
        message: str,
        *,
        role: str = "assistant",
    ):
        await self.new(context, role)
        x = await self.reply(context, message)
        await self.stop(context)

        return x
