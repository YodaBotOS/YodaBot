import asyncio
import typing

import openai

SUPPORTED_LANGUAGES = ["Bash", "C#", "Go", "Java", "JavaScript", "Python", "Ruby", "Rust", "SQL", "TypeScript"]
SUPPORTED_LANGUAGES_LITERAL = typing.Literal[tuple(SUPPORTED_LANGUAGES)]  # type: ignore


class Codex:
    COMMENTS = {
        "Bash": "#",
        "C#": "//",
        "Go": "//",
        "Java": "//",
        "JavaScript": "//",
        "Python": "#",
        "Ruby": "#",
        "Rust": "//",
        "SQL": "--",
        "TypeScript": "//",
    }

    FILE = {
        "Bash": "bash",
        "C#": "cs",
        "Go": "go",
        "Java": "java",
        "JavaScript": "js",
        "Python": "py",
        "Ruby": "rb",
        "Rust": "rs",
        "SQL": "sql",
        "TypeScript": "ts",
    }

    LOWERED_CHARS = {
        "bash": "Bash",
        "c#": "C#",
        "go": "Go",
        "java": "Java",
        "javascript": "JavaScript",
        "python": "Python",
        "ruby": "Ruby",
        "rust": "Rust",
        "sql": "SQL",
        "typescript": "TypeScript",
    }

    MODEL = "code-davinci-002"

    COMPLETION_KWARGS = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 512,
        "top_p": 1,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.3,
    }

    EXPLAIN_KWARGS = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 100,
        "top_p": 1,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stop": ['"""'],
    }

    lock = asyncio.Semaphore()

    @staticmethod
    def _do_comments(language: SUPPORTED_LANGUAGES_LITERAL, text: str) -> str:
        s = ""

        for line in text.splitlines():
            s += f"\n{Codex.COMMENTS[language]} {line}"

        return s.strip()

    @staticmethod
    def _remove_comments(language: SUPPORTED_LANGUAGES_LITERAL, text: str):
        s = ""

        for txt in text.splitlines():
            if txt.startswith(Codex.COMMENTS[language]):
                s += f"\n{txt[len(Codex.COMMENTS[language]):].strip()}"

        return s.strip()

    @staticmethod
    async def completion(language: SUPPORTED_LANGUAGES_LITERAL, prompt: str, *, user: int, n: int = 3) -> list[str]:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language {language} is not supported")

        comment_prefix = Codex.COMMENTS[language]

        if language == "Python":
            parsed_prompt = f'"""\n{prompt}\n"""'
        else:
            parsed_prompt = Codex._do_comments(language, prompt)

        passed_prompt = f"{comment_prefix} {language}\n{parsed_prompt}\n\n"

        async with Codex.lock:
            response = openai.Completion.create(
                **Codex.COMPLETION_KWARGS,
                prompt=passed_prompt,
                n=n,
                user=str(user),
            )

            choices = []

            for choice in response["choices"]:
                text = choice["text"].strip()

                c = choice.copy()

                while c["finish_reason"] == "length":
                    await asyncio.sleep(1.5)

                    response = openai.Completion.create(
                        **Codex.COMPLETION_KWARGS,
                        prompt=passed_prompt + text,
                        user=str(user),
                    )

                    c = response["choices"][0]

                    text += c["text"]

                choices.append(text)

        return list(set(choices))  # remove duplicates (lazy to do it the hard way)

    @staticmethod
    async def explain(language: SUPPORTED_LANGUAGES_LITERAL, code: str, *, user: int) -> str:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language {language} is not supported")

        prompt = f"Here's what the above {language} code is doing:\n"

        if language == "Python":
            passed_prompt = f'{code}\n\n"""\n{prompt}'
        else:
            passed_prompt = f"{code}\n\n{Codex._do_comments(language, prompt)}"

        async with Codex.lock:
            response = openai.Completion.create(
                **Codex.EXPLAIN_KWARGS,
                prompt=passed_prompt,
                user=str(user),
            )

            choice = response["choices"][0]

            text = choice["text"].strip()

            if language != "Python":
                text = Codex._remove_comments(language, text)

            c = choice.copy()

            while c["finish_reason"] == "length":
                await asyncio.sleep(1.5)

                response = openai.Completion.create(
                    **Codex.EXPLAIN_KWARGS,
                    prompt=passed_prompt + text,
                    user=str(user),
                )

                c = response["choices"][0]

                if language != "Python":
                    c["text"] = Codex._remove_comments(language, c["text"])

                text += c["text"]

        return text
