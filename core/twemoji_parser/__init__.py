import json
import os
import subprocess


class TwemojiParser:
    """
    parser = TwemojiParser()
    parser.parse_emoji("🤔") # {"url": "...", "indices": [...], "text": "...", "type": "emoji"}
    """

    def __init__(self):
        if not self.check_node_installed():
            raise Exception("Node.js is not installed.")

        if not self.check_npm_installed():
            raise Exception("npm is not installed.")

        self.install_twemoji_parser()

    @staticmethod
    def check_node_installed():
        try:
            subprocess.Popen(["node", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def check_npm_installed():
        try:
            subprocess.Popen(["npm", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def install_twemoji_parser():
        process = subprocess.Popen(
            ["npm", "install", "twemoji-parser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return process, process.communicate()

    @staticmethod
    def get_twemoji_file_path():
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "src/parser.js")

    def _run(self, *args):
        path = self.get_twemoji_file_path()

        process = subprocess.Popen(["node", path, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if stderr:
            raise Exception(stderr.decode())

        return stdout.decode()

    def parse(self, text: str, *, svg: bool = False) -> list[dict[str, str | list[int]]]:
        js = json.loads(self._run(f'"{text}"'))

        if not svg:
            for i in js:
                i["url"] = i["url"].replace("svg/", "72x72/").replace(".svg", ".png")

        return js

    def full_parse(self, text: str, *, svg: bool = False) -> dict[str, str | list[int]] | None:
        if len(text) == 1:
            return self.parse(text, svg=svg)[0]

        return None
