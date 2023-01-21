import re
import typing

import openai


class OpenAI:
    CHAT_START_STRING = """
The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.

Human: Hello, who are you?
AI: I am a bot.
Human: Who are you?
AI: I am a bot.
Human:"""
    CHAT_PARAMS = {
        "model": "text-davinci-003",
        "temperature": 0.9,
        "max_tokens": 150,
        "top_p": 1,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.6,
        "stop": [" Human:", " AI:", "Human:", "AI:"],
    }

    GRAMMAR_CORRECTION_START_STRING = "Correct this to standard English:\n\n{text}\n\n"
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

    def __init__(self, key: str = None, *, strip_strings: bool = True):
        if key is not None:
            self.key = key
            openai.api_key = key
        else:
            self.key = openai.api_key

        self.strip_strings = strip_strings

        self.chat_ids = {}

    # --- Chat ---
    def _create_chat(self, user, channel, *, force=False):
        if (user, channel) in self.chat_ids:
            if force:
                self.chat_ids[(user, channel)] = {"text": self.CHAT_START_STRING}

            return self.chat_ids[(user, channel)]

        self.chat_ids[(user, channel)] = {"text": self.CHAT_START_STRING}

        return self.chat_ids[(user, channel)]

    def _set_chat(self, text, user, channel):
        chat_id = self._create_chat(user, channel)

        chat_id["text"] = text

        return chat_id

    def _append_chat(self, text, user, channel, *, human=True):
        chat_id = self._create_chat(user, channel)

        if human:
            x = "Human"
            y = "AI"
        else:
            x = "AI"
            y = "Human"

        chat_id["text"] += f" {text}\n{y}:"

        return chat_id

    def _strip_chat(self, user, channel, *, force=True):
        chat_id = self._create_chat(user, channel)
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
    ) -> str:
        text = self.clean_chat(text)

        if user and channel:
            self._append_chat(text, user, channel, human=True)

            chat_id = self._create_chat(user, channel)

            text = chat_id["text"]

            response = openai.Completion.create(prompt=text, **self.CHAT_PARAMS)

            if force_return_data:
                return response

            ai_resps = response["choices"][0]["text"].strip()

            if not ai_resps:
                ai_resps = "Sorry, I did not understand."

            self._append_chat(ai_resps, user, channel, human=False)

            return ai_resps
        elif user or channel:
            raise Exception("Both user and channel must be specified")
        else:
            start_string = self.CHAT_START_STRING.strip() + f"Human: {text}\n"

            response = openai.Completion.create(prompt=text, **self.CHAT_PARAMS)

            ai_resps = response["choices"][0]["text"].strip()

            if not ai_resps:
                ai_resps = "Sorry, I did not understand."

            return ai_resps

    # --- Grammar Correction ---
    def grammar_correction(self, text: str, *, raw: bool = False) -> str | typing.Any:
        prompt = self.GRAMMAR_CORRECTION_START_STRING.format(text=text)

        response = openai.Completion.create(prompt=prompt, **self.GRAMMAR_CORRECTION_PARAMS)

        if raw:
            return response

        return response["choices"][0]["text"].strip()

    # --- Study Notes ---
    def study_notes(self, topic: str, *, amount: int = 5, raw: bool = False) -> str | typing.Any:
        amount = min(max(1, amount), 10)  # only numbers between 1-10 only allowed

        prompt = self.STUDY_NOTES_START_STRING.format(topic=topic, amount=amount)

        response = openai.Completion.create(prompt=prompt, **self.STUDY_NOTES_PARAMS)

        if raw:
            return response

        text = "1. " + response["choices"][0]["text"].strip()

        text = re.sub("\n+", "\n", text)

        return text
