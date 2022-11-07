import re
import unicodedata

import discord
from discord.ext import commands
from discord.ext.commands import Converter

from core.twemoji_parser import TwemojiParser


parser = TwemojiParser()


class _ImageConverter(Converter):
    """
    Process of Checking in Image Converter:

    1. Check argument for URL
    2. Check argument for User/Member (ID, Username, Nickname or Mention), and return their display avatar URL
    3. Check for emoji in argument
    4. Check message for attachments
    5. Check message for stickers
    6. Check message reference for attachments
    7. Check message reference for URL in content
    8. Check message reference for Embed Image
    9. Check message reference for Embed Thumbnail
    10. Check message for reference. If it has, return their display avatar URL

    If none of this is True:
        If argument is None:
            Return the author's display avatar url (which will never fail cause it is a display avatar)
        Else:
            Raise error saying that argument is not valid.
    """
    async def convert(self, ctx: commands.Context, argument: str) -> str | None:
        if match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", argument):
            return match.group(0)


class ImageConverter(Converter):
    def __init__(self, *, with_member: bool = False, with_emoji: bool = False):
        self.with_member = with_member
        self.with_emoji = with_emoji

    async def convert(self, ctx: commands.Context, argument: str | None) -> str | None:
        if argument:
            if match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", argument):
                return match.group(0)

        # Please ignore the variable names, thx!
        if msgattach := ctx.message.attachments:
            return msgattach[0].url
        
        if msgsticker := ctx.message.stickers:
            if msgsticker[0].format == discord.StickerFormatType.png:
                return msgsticker[0].url

        if self.with_member:
            if mention := re.fullmatch(r'<@!?(\d+)>', argument):
                user_id = int(mention.group(1))

                try:
                    user = ctx.bot.get_user(user_id) or await ctx.bot.fetch_user(user_id)
                except:
                    user = None

                if user:
                    return user.avatar.url

        if self.with_emoji:
            try:
                em = await commands.EmojiConverter().convert(ctx, argument)
                return em.url
            except:
                if result := parser.full_parse(argument):
                    digit = f'{ord(result["text"]):x}'

                    url = f'https://twemoji.maxcdn.com/2/72x72/{digit}.png'

                    async with ctx.bot.session.get(url) as resp:
                        if resp.status == 200:
                            return url
                        else:
                            return result['url']

        if reply := ctx.message.reference:
            msgreply = reply.resolved

            if msgreplycontent := msgreply.content:
                if match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                                         msgreplycontent):
                    return match.group(0)

            if msgreplyattach := msgreply.attachments:
                return msgreplyattach[0].url

            if msgsticker := msgreply.stickers:
                if msgsticker[0].format == discord.StickerFormatType.png:
                    return msgsticker[0].url

            if msgreplyembed := msgreply.embeds:
                if msgreplyembed[0].image:
                    return msgreplyembed[0].image.url

                if msgreplyembed[0].thumbnail:
                    return msgreplyembed[0].thumbnail.url


class AttachmentConverter(Converter):
    URL_REGEX = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        if match := self.URL_REGEX.fullmatch(argument):
            return match.group(0)

        if msgattach := ctx.message.attachments:
            return msgattach[0].url

        if reply := ctx.message.reference:
            msgreply = reply.resolved

            if msgreplycontent := msgreply.content:
                if match := self.URL_REGEX.fullmatch(msgreplycontent):
                    return match.group(0)

            if msgreplyattach := msgreply.attachments:
                return msgreplyattach[0].url

            if msgreplyembed := msgreply.embeds:
                if msgreplyembed[0].image:
                    return msgreplyembed[0].image.url

                if msgreplyembed[0].thumbnail:
                    return msgreplyembed[0].thumbnail.url


class SizeConverter(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> tuple[int, int]:
        try:
            width, height = argument.split('x')

            return int(width), int(height)
        except:
            raise commands.BadArgument("Invalid size provided.")
