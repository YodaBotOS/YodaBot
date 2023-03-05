from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from core.bot import Bot

import openai

from .chat import Chat
from .codex import Codex


class OpenAI:
    GRAMMAR_CORRECTION_START_STRING = "Correct this to standard English:\n\n{text}\n\n"
    GRAMMAR_CORRECTION_REPHRASE_START_STRING = "Correct this to standard English as well as replace complicated sentences with more efficient ones, refresh repetitive language, and uphold accurate spelling, punctuation, and grammar:\n\n{text}\n\n"
    GRAMMAR_CORRECTION_PARAMS = {
        "model": "text-davinci-003",
        "temperature": 0,
        "max_tokens": 400,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

    STUDY_NOTES_START_STRING = "What are {amount} key points I should know when studying {topic}?\n\n1."
    STUDY_NOTES_PARAMS = {
        "model": "text-davinci-003",
        "temperature": 0.3,
        "max_tokens": 400,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
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
    WORDTUNES_START_STRING = "Make {amount} sentences about this with {tones} tone:\n\n{text}\n\n1."
    WORDTUNES_PARAMS = {
        "model": "text-davinci-003",
        "temperature": 0,
        "max_tokens": 400,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
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

        response = await openai.Completion.acreate(prompt=prompt, user=str(user), **self.GRAMMAR_CORRECTION_PARAMS)

        if raw:
            return response

        return response["choices"][0]["text"].strip()

    # --- Study Notes ---
    async def study_notes(self, topic: str, *, user: int, amount: int = 5, raw: bool = False) -> str | typing.Any:
        amount = min(max(1, amount), 10)  # only numbers between 1-10 only allowed

        prompt = self.STUDY_NOTES_START_STRING.format(topic=topic, amount=amount)

        response = await openai.Completion.acreate(prompt=prompt, user=str(user), **self.STUDY_NOTES_PARAMS)

        if raw:
            return response

        text = "1. " + response["choices"][0]["text"].strip()

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

        response = await openai.Completion.acreate(prompt=prompt, user=str(user), **self.WORDTUNES_PARAMS)

        if raw:
            return response

        text = "1. " + response["choices"][0]["text"].strip()

        text = re.sub("\n+", "\n", text)

        return text

    @property
    def codex(self) -> Codex:
        return Codex()

    @property
    def chat(self) -> Chat:
        return Chat(self)
