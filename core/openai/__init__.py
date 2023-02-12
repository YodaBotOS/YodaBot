import re
import typing

import openai

from .codex import Codex


class OpenAI:
    CHAT_START_STRING = """
The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly. This AI is more into human conversations than as an Assistant, but still gives out inforrmation/facts. The AI is chatting with "{username}" (with a whole username of "{user}") with the user ID of {userid}.

Human: Hello, who are you?
AI: I am YodaBot.
Human: Who are you?
AI: I am YodaBot.
Human: Who am I?
AI: Your name is {username} ({user})
Human: Who is {username}?
AI: You."""

    CHAT_PARAMS = {
        "model": "text-curie-001",
        "temperature": 0.9,
        "max_tokens": 150,
        "top_p": 1,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.6,
        "stop": [" Human:", " AI:", "Human:", "AI:"],
    }

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

    def __init__(self, key: str = None, *, strip_strings: bool = True):
        if key is not None:
            self.key = key
            openai.api_key = key
        else:
            self.key = openai.api_key

        self.strip_strings = strip_strings

        self.chat_ids = {}

    # --- Chat ---
    def _create_chat(self, user, channel, usr, *, force=False):
        if (user, channel) in self.chat_ids:
            if force:
                self.chat_ids[(user, channel)] = {
                    "text": self.CHAT_START_STRING.strip().format(user=usr.name, username=str(usr), userid=usr.id)
                }

            return self.chat_ids[(user, channel)]

        self.chat_ids[(user, channel)] = {
            "text": self.CHAT_START_STRING.strip().format(user=usr.name, username=str(usr), userid=usr.id)
        }

        return self.chat_ids[(user, channel)]

    def _set_chat(self, text, user, channel, usr):
        chat_id = self._create_chat(user, channel, usr)

        chat_id["text"] = text

        return chat_id

    def _append_chat(self, text, user, channel, usr, *, human=True):
        chat_id = self._create_chat(user, channel, usr)

        if human:
            x = "Human"
            y = "AI"
        else:
            x = "AI"
            y = "Human"

        chat_id["text"] += f" {text}\n{y}:"

        return chat_id

    def _strip_chat(self, user, channel, usr, *, force=True):
        chat_id = self._create_chat(user, channel, usr)
        text = chat_id["text"]

        if self.strip_strings:
            text = text.strip()
        else:
            if force:
                text = text.strip()

        chat_id["text"] = text

        return chat_id

    def clean_chat(self, text):
        if self.strip_strings:
            text = text.strip()

        text = text.replace("\n", " ").replace("AI:", "").replace("Human:", "")

        return text

    def stop_chat(self, user: int, channel: int):
        try:
            del self.chat_ids[(user, channel)]
        except KeyError:
            pass

    def chat(
        self,
        text: str,
        *,
        user: int = None,
        channel: int = None,
        force_return_data: bool = False,
        usr=None,
    ) -> str:
        text = self.clean_chat(text)

        if user and channel:
            self._append_chat(text, user, channel, usr, human=True)

            chat_id = self._create_chat(user, channel, usr=usr)

            text = chat_id["text"]

            response = openai.Completion.create(prompt=text, user=str(user), **self.CHAT_PARAMS)

            if force_return_data:
                return response

            ai_resps = response["choices"][0]["text"].strip()

            if not ai_resps:
                ai_resps = "Sorry, I did not understand."

            self._append_chat(ai_resps, user, channel, usr, human=False)

            return ai_resps
        elif user or channel:
            raise Exception("Both user and channel must be specified")
        else:
            start_string = (
                self.CHAT_START_STRING.strip().format(user=usr.name, username=str(usr), userid=usr.id)
                + f"Human: {text}\nAI: "
            )

            response = openai.Completion.create(prompt=start_string, user=str(user), **self.CHAT_PARAMS)

            ai_resps = response["choices"][0]["text"].strip()

            if not ai_resps:
                ai_resps = "Sorry, I did not understand."

            return ai_resps

    # --- Grammar Correction ---
    def grammar_correction(
        self, text: str, *, user: int, rephrase: bool = False, raw: bool = False
    ) -> str | typing.Any:
        if rephrase:
            prompt = self.GRAMMAR_CORRECTION_REPHRASE_START_STRING
        else:
            prompt = self.GRAMMAR_CORRECTION_START_STRING

        prompt = prompt.format(text=text)

        response = openai.Completion.create(prompt=prompt, user=str(user), **self.GRAMMAR_CORRECTION_PARAMS)

        if raw:
            return response

        return response["choices"][0]["text"].strip()

    # --- Study Notes ---
    def study_notes(self, topic: str, *, user: int, amount: int = 5, raw: bool = False) -> str | typing.Any:
        amount = min(max(1, amount), 10)  # only numbers between 1-10 only allowed

        prompt = self.STUDY_NOTES_START_STRING.format(topic=topic, amount=amount)

        response = openai.Completion.create(prompt=prompt, user=str(user), **self.STUDY_NOTES_PARAMS)

        if raw:
            return response

        text = "1. " + response["choices"][0]["text"].strip()

        text = re.sub("\n+", "\n", text)

        return text

    # --- Wordtune ---
    def wordtune(
        self, text: str, tones: list[str], amount: int = 5, *, user: int, raw: bool = False
    ) -> str | typing.Any:
        amount = min(max(1, amount), 10)  # only numbers between 1-10 only allowed

        if isinstance(tones, list):
            tones = ", ".join(tones)

        prompt = self.WORDTUNES_START_STRING.format(text=text, amount=amount, tones=tones)

        response = openai.Completion.create(prompt=prompt, user=str(user), **self.WORDTUNES_PARAMS)

        if raw:
            return response

        text = "1. " + response["choices"][0]["text"].strip()

        text = re.sub("\n+", "\n", text)

        return text

    @property
    def codex(self) -> Codex:
        return Codex()
