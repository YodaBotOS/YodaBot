import re

import discord
from discord.ext import commands
from discord.ext.commands import Converter

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
    async def convert(self, ctx: commands.Context, argument: str) -> str | None:
        if argument:
            if match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", argument):
                return match.group(0)

        # Please ignore the variable names, thx!
        if msgattach := ctx.message.attachments:
            return msgattach[0].url

        if reply := ctx.message.reference:
            msgreply = reply.resolved

            if msgreplycontent := msgreply.content:
                if match := re.fullmatch(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                                         msgreplycontent):
                    return match.group(0)

            if msgreplyattach := msgreply.attachments:
                return msgreplyattach[0].url

            if msgreplyembed := msgreply.embeds:
                if msgreplyembed[0].image:
                    return msgreplyembed[0].image.url

                if msgreplyembed[0].thumbnail:
                    return msgreplyembed[0].thumbnail.url
