from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from core.bot import Bot

import openai

from .chat import Chat, GoogleChat
from .codex import Codex


class OpenAI:
    GRAMMAR_CORRECTION_SYSTEM = "You are a helpful assistant that can correct text to standard English. Do not explain why the text is incorrect, but rather return only the corrected text."
    GRAMMAR_CORRECTION_START_STRING = "Correct this to standard English: {text}"
    GRAMMAR_CORRECTION_REPHRASE_SYSTEM = "You are a helpful assistant that can correct text to standard English as well as replace complicated sentences with more efficient ones, refresh repetitive language, and uphold accurate spelling, punctuation, and grammar."
    GRAMMAR_CORRECTION_REPHRASE_START_STRING = "Fix this sentence: {text}"
    GRAMMAR_CORRECTION_PARAMS = {
        "model": "gpt-4",
        # "temperature": 0,
        # "max_tokens": 400,
        # "top_p": 1.0,
        # "frequency_penalty": 0.0,
        # "presence_penalty": 0.0,
    }

    STUDY_NOTES_SYSTEM = "You are a helpful assistant that can make some key points when studying about a certain topic. Do not explain the topic in detail, but rather make some key points that you should know when studying about it. If the user asks for multiple of them, send them in a numbered list."
    STUDY_NOTES_START_STRING = "What are {amount} key points I should know when studying {topic}?"
    STUDY_NOTES_PARAMS = {
        "model": "gpt-4",
        # "temperature": 0.3,
        # "max_tokens": 400,
        # "top_p": 1.0,
        # "frequency_penalty": 0.0,
        # "presence_penalty": 0.0,
    }

    WORDTUNES = {
        "Formal",
        "Informal",
        "Casual",
        "Sad",
        "Confident",
        "Curious",
        "Surprised",
        "Unassuming",
        "Concerned",
        "Joyful",
        "Disheartening",
        "Worried",
        "Excited",
        "Regretful",
        "Encouraging",
        "Assertive",
        "Optimistic",
        "Accusatory",
        "Egocentric",
        "Appreciative",
        "Disapproving",
    }
    WORDTUNES_EMOJIS = {
        "Formal": None,
        "Informal": None,
        "Casual": "\U0001f60b",
        "Sad": "\U0001f62d",
        "Confident": "\U0001f91d",
        "Curious": "\U0001f914",
        "Surprised": "\U0001f62f",
        "Unassuming": "\U0001f644",
        "Concerned": "\U0001f61f",
        "Joyful": "\U0001f642",
        "Disheartening": "\U0001f614",
        "Worried": "\U0001f628",
        "Excited": "\U0001f60d",
        "Regretful": "\U0001f972",
        "Encouraging": "\U0001f44d",
        "Assertive": "\U0001f44a",
        "Optimistic": "\U0001f60e",
        "Accusatory": "\U0001f44e",
        "Egocentric": "\U0001f9d0",
        "Joyful": "\U0001f642",
        "Appreciative": "\U0001f64c",
        "Disapproving": "\U0001f645",
    }
    WORDTUNES_LITERAL = typing.Literal[
        "Formal",
        "Informal",
        "Casual",
        "Sad",
        "Confident",
        "Curious",
        "Surprised",
        "Unassuming",
        "Concerned",
        "Joyful",
        "Disheartening",
        "Worried",
        "Excited",
        "Regretful",
        "Encouraging",
        "Assertive",
        "Optimistic",
        "Accusatory",
        "Egocentric",
        "Appreciative",
        "Disapproving",
    ]
    WORDTUNES_SYSTEM = "You are a helpful assistant that can make sentences with a certain tone. Do not explain how the sentence is formed. Only return the sentence(s) with the tone. If the user asks for multiple of them, send them in a numbered list."
    WORDTUNES_START_STRING = "Make {amount} sentences about this with {tones} tone in the following sentence: {text}"
    WORDTUNES_PARAMS = {
        "model": "gpt-4",
        # "temperature": 0,
        # "max_tokens": 400,
        # "top_p": 1.0,
        # "frequency_penalty": 0.0,
        # "presence_penalty": 0.0,
    }

    def __init__(self, key: str = None, *, strip_strings: bool = True, bot: Bot = None):
        if key is not None:
            self.key = key
            openai.api_key = key
        else:
            self.key = openai.api_key

        self.strip_strings = strip_strings

        self.chat_ids = {}

        self.bot = bot

    # --- Grammar Correction ---
    async def grammar_correction(
        self, text: str, *, user: int, rephrase: bool = False, raw: bool = False
    ) -> str | typing.Any:
        if rephrase:
            prompt = self.GRAMMAR_CORRECTION_REPHRASE_START_STRING
        else:
            prompt = self.GRAMMAR_CORRECTION_START_STRING

        prompt = prompt.format(text=text)

        response = await openai.ChatCompletion.acreate(
            **self.GRAMMAR_CORRECTION_PARAMS,
            messages=[
                {"role": "system", "content": self.GRAMMAR_CORRECTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            user=str(user),
        )

        if raw:
            return response

        return response["choices"][0]["message"]["content"].strip()

    # --- Study Notes ---
    async def study_notes(self, topic: str, *, user: int, amount: int = 5, raw: bool = False) -> str | typing.Any:
        amount = min(max(1, amount), 10)  # only numbers between 1-10 only allowed

        prompt = self.STUDY_NOTES_START_STRING.format(topic=topic, amount=amount)

        response = await openai.ChatCompletion.acreate(
            **self.STUDY_NOTES_PARAMS,
            messages=[{"role": "system", "content": self.STUDY_NOTES_SYSTEM}, {"role": "user", "content": prompt}],
            user=str(user),
        )

        if raw:
            return response

        text = response["choices"][0]["message"]["content"].strip()

        text = re.sub("\n+", "\n", text)

        return text

    # --- Wordtune ---
    async def wordtune(
        self, text: str, tones: list[str], amount: int = 5, *, user: int, raw: bool = False
    ) -> str | typing.Any:
        amount = min(max(1, amount), 10)  # only numbers between 1-10 only allowed

        if isinstance(tones, list):
            tones = ", ".join(tones)

        prompt = self.WORDTUNES_START_STRING.format(text=text, amount=amount, tones=tones)

        response = await openai.ChatCompletion.acreate(
            **self.WORDTUNES_PARAMS,
            messages=[{"role": "system", "content": self.WORDTUNES_SYSTEM}, {"role": "user", "content": prompt}],
            user=str(user),
        )

        if raw:
            return response

        text = response["choices"][0]["message"]["content"].strip()

        text = re.sub("\n+", "\n", text)

        return text

    @property
    def codex(self) -> Codex:
        return Codex()

    @property
    def chat(self) -> Chat:
        return Chat(self)

    def googlechat(self, serp_api_key: str) -> GoogleChat:
        return GoogleChat(serp_api_key, self)
