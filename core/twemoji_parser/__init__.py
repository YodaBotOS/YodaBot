import re
import typing

import emoji


class TwemojiParser:
    """
    parser = TwemojiParser()
    parser.parse_emoji("🤔") # {"url": "...", "indices": [...], "text": "...", "type": "emoji"}
    """

    ASSET_TYPE = typing.Literal["png", "svg"]

    def __init__(self):
        # self.vs16_regex = re.compile("\uFE0F")
        # self.zero_width_joiner = "\u200d"
        ...

    # def remove_vs16s(self, raw_emoji: str) -> str:
    #     if self.zero_width_joiner not in raw_emoji:
    #         return re.sub(self.vs16_regex, '', raw_emoji)
    #     else:
    #         return raw_emoji

    @staticmethod
    def get_twemoji_url(codepoints: str, asset_type: ASSET_TYPE) -> str:
        if asset_type == "png":
            return f"https://twemoji.maxcdn.com/v/latest/72x72/{codepoints}.png"
        else:
            return f"https://twemoji.maxcdn.com/v/latest/svg/{codepoints}.svg"

    def parse(
        self, text: str, *, svg: bool = False
    ) -> list[dict[str, str | list[int]]]:
        asset_type = "svg" if svg else "png"
        emojis = emoji.emoji_list(text)
        entities = []

        for emoji_dict in emojis:
            emoji_text = emoji_dict["emoji"]
            codepoints = "-".join(
                hex(ord(c))[2:] for c in emoji_text
            )  # "-".join(hex(ord(c))[2:] for c in self.remove_vs16s(emoji_text))
            entities.append(
                {
                    "url": (
                        self.get_twemoji_url(codepoints, asset_type)
                        if codepoints
                        else ""
                    ),
                    "indices": [emoji_dict["match_start"], emoji_dict["match_end"]],
                    "text": emoji_text,
                    "type": "emoji",
                }
            )

        return entities

    def full_parse(
        self, text: str, *, svg: bool = False
    ) -> dict[str, str | list[int]] | None:
        if len(text) == 1:
            return self.parse(text, svg=svg)[0]

        return None

    def __call__(
        self, text: str, *, svg: bool = False
    ) -> list[dict[str, str | list[int]]]:
        return self.parse(text, svg=svg)
