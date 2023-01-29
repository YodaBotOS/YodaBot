from __future__ import annotations

import importlib
import inspect
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str as _T
from discord.ext import commands
from discord.utils import as_chunks as chunker

from core import translate
from core.context import Context
from utils.paginator import YodaMenuPages
from utils.translate import TranslateLanguagesPaginator

if TYPE_CHECKING:
    from core.bot import Bot


class Translate(commands.Cog):
    """
    Translates a text
    """

    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.translate: translate.Translate = None

        self.ctx_menu = app_commands.ContextMenu(
            name=_T("Translate"),
            callback=self.translate_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_load(self):
        importlib.reload(translate)
        from core.translate import Translate

        self.bot.translate = Translate(self.bot.config.PROJECT_ID, session=self.bot.session)
        await self.bot.translate.get_languages(force_call=True, add_to_cache=True)
        self.translate: Translate = self.bot.translate

        # self.languages = list(chunker(self.bot.translate.languages, 10))

    async def cog_unload(self):
        self.translate = None
        del self.bot.translate

        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def translate_func(self, ctx, text, to, _from) -> discord.Embed | str:
        newline = "\n"

        text = await commands.clean_content(fix_channel_mentions=True, escape_markdown=True).convert(ctx, text)

        if len(text) > 1024:
            return "TEXT_TOO_LARGE"

        to = to.strip()

        if _from:
            _from = _from.strip()

        to_lang = self.translate.get_language(to)

        if not to_lang:
            return "TO_LANG_INVALID"

        if _from:
            from_lang = self.translate.get_language(_from)

            if not from_lang:
                return "FROM_LANG_INVALID"
        else:
            from_lang = await self.translate.detect_language(text)
            from_lang = self.translate.get_language(from_lang["languageCode"])

        if from_lang["languageCode"] == to_lang["languageCode"]:
            # Do input tools instead
            input_tools = await self.translate.input_tools(text, from_lang["languageCode"])

            embed = discord.Embed(color=self.bot.color)
            embed.title = "Translation Result:"

            embed.description = f"""
**From:** {from_lang["displayName"]}
```
{text}
```{f"*Translating `{input_tools['choices'][0]}`{newline}" if input_tools['choices'][0] != text else ""}
**To:** {to_lang["displayName"]}
```
{input_tools["choices"][0]}
```
            """

            return embed

        input_tools = await self.translate.input_tools(text, from_lang["languageCode"])
        original_text = text
        text = input_tools["choices"][0]
        trans = await self.translate.translate(text, to_lang["languageCode"], source_language=from_lang["languageCode"])

        embed = discord.Embed(color=self.bot.color)
        embed.title = "Translation Result:"

        embed.description = f"""
**From:** {from_lang["displayName"]}
```
{original_text}
```{f"*Translating `{input_tools['choices'][0]}`{newline}" if input_tools['choices'][0] != original_text else ""}
**To:** {to_lang["displayName"]}
```
{trans["translated"]}
```
        """

        return embed

    @app_commands.command(name=_T("translate"))
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.rename(_from=_T("from"))
    @app_commands.describe(
        text=_T("The text to be translated"),
        to=_T("The language to translate to"),
        _from=_T("The language to translate from"),
    )
    async def translate_slash(self, interaction: discord.Interaction, text: str, to: str, _from: str = None):
        """
        Tries to Translate a text to another language.
        """

        ctx = await Context.from_interaction(interaction)

        await interaction.response.defer()

        result = await self.translate_func(ctx, text, to, _from)

        if isinstance(result, discord.Embed):
            return await interaction.followup.send(embed=result)

        if result == "TEXT_TOO_LARGE":
            return await interaction.followup.send("Text is too large to translate.", ephemeral=True)
        elif result == "TO_LANG_INVALID":
            return await interaction.followup.send(f"Language `{to}` not found.", ephemeral=True)
        elif result == "FROM_LANG_INVALID":
            return await interaction.followup.send(f"Language `{_from}` not found.", ephemeral=True)
        else:
            return await interaction.followup.send(f"An error occurred, please report this error: {result}")

    @translate_slash.autocomplete("to")
    async def translate_to_autocomplete(self, interaction: discord.Interaction, current: str):
        langs = self.translate.get_all_languages(only="displayName")

        if not current:
            return [app_commands.Choice(name=x, value=x) for x in langs[:25]]

        langs = self.translate.get_all_languages()

        choices = []

        match = self.translate.get_language(current)

        if match:
            choices.append(app_commands.Choice(name=match["displayName"], value=match["displayName"]))

        for lang in langs:
            if len(choices) >= 25:
                break

            if lang.startswith(current):
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if lang.lower().startswith(current.lower()):
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if current in lang:
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if current.lower() in lang:
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        return choices[:25]

    @translate_slash.autocomplete("_from")
    async def translate_from_autocomplete(self, interaction: discord.Interaction, current: str):
        langs = self.translate.get_all_languages()

        if not current:
            return [app_commands.Choice(name=x, value=x) for x in langs[:25]]

        choices = []

        match = self.translate.get_language(current)

        if match:
            choices.append(app_commands.Choice(name=match["displayName"], value=match["displayName"]))

        for lang in langs:
            if len(choices) >= 25:
                break

            if lang.startswith(current):
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if lang.lower().startswith(current.lower()):
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if current in lang:
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if current.lower() in lang:
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        return choices[:25]

    @app_commands.command(name=_T("translate-languages"))
    @app_commands.describe(query=_T("The language you want to search for."))
    async def translate_languages_slash(self, interaction: discord.Interaction, query: str = None):
        """
        Shows a list of languages that can be translated to.
        """

        await interaction.response.defer()

        if query:
            query = query.strip()

            lang = self.translate.get_language(query)

            if not lang:
                return await interaction.followup.send(f"Language `{query}` not found.", ephemeral=True)

            lang_code = lang["languageCode"]
            lang_name = lang["displayName"]

            embed = discord.Embed(color=self.bot.color)
            embed.title = lang_name

            embed.description = f"**Language Name:** {lang_name}\n**Language Code:** {lang_code}"

            return await interaction.followup.send(embed=embed)

        ctx = await Context.from_interaction(interaction)

        source = TranslateLanguagesPaginator(self.translate.languages, per_page=10)
        menu = YodaMenuPages(source, delete_message_after=True)
        return await menu.start(ctx, channel=interaction.followup)

    @translate_languages_slash.autocomplete("query")
    async def translate_languages_slash_query_autocomplete(self, interaction: discord.Interaction, current: str):
        langs = self.translate.get_all_languages(only="displayName")

        if not current:
            return [app_commands.Choice(name=x, value=x) for x in langs[:25]]

        langs = self.translate.get_all_languages()

        choices = []

        match = self.translate.get_language(current)

        if match:
            choices.append(app_commands.Choice(name=match["displayName"], value=match["displayName"]))

        for lang in langs:
            if len(choices) >= 25:
                break

            if lang.startswith(current):
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if lang.lower().startswith(current.lower()):
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if current in lang:
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        if len(choices) >= 25:
            return choices[:25]

        for lang in langs:
            if len(choices) >= 25:
                break

            if current.lower() in lang:
                if lang in [x.name for x in choices]:
                    continue

                choices.append(app_commands.Choice(name=lang, value=lang))

        return choices[:25]

    @commands.group(name="translate", invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def translate(self, ctx: Context, lang: str, *, text: str = None):
        """
        Tries to Translate a text to another language.

        Example:
            - `yoda translate fr Hello!`
            - `yoda translate en-dutch What are you doing?`
            - `yoda translate "chinese (simplified)-English" 你好`
            - `yoda translate English-Spanish Hello!`
        """

        if ctx.subcommand_passed:
            return await ctx.send_help(ctx.command)

        if text is None:
            if not (ref := ctx.message.reference):
                raise commands.MissingRequiredArgument(
                    inspect.Parameter("text", inspect.Parameter.KEYWORD_ONLY, annotation=str)
                )

            text = ref.resolved.content

        if "-" in lang:
            langs = self.translate.get_all_languages()
            if lang not in langs:
                _from, to = lang.split("-")
                return await self.translate_from(ctx, _from, to, text=text)

        async with ctx.typing():
            result = await self.translate_func(ctx, text, lang, None)

            if isinstance(result, discord.Embed):
                return await ctx.send(embed=result)

            if result == "TEXT_TOO_LARGE":
                return await ctx.send("Text is too large to translate.", ephemeral=True)
            elif result == "TO_LANG_INVALID":
                return await ctx.send(f"Language `{lang}` not found.", ephemeral=True)
            # elif result == "FROM_LANG_INVALID":
            #     return await ctx.send(f"Language `{_from}` not found.", ephemeral=True)
            else:
                return await ctx.send(f"An error occurred, please report this error: {result}")

    @translate.command(name="from", usage="<from> <to> [text]")
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def translate_from(self, ctx: Context, _from: str, to: str, *, text: str = None):
        """
        Tries to Translate a text to another language, with the specified source (original text) language.

        Example:
            - `yoda translate from en dutch Hello!`
            - `yoda translate from "chinese (simplified)" English 你好`
            - `yoda translate from English Spanish Hello!`
        """

        if text is None:
            if not (ref := ctx.message.reference):
                raise commands.MissingRequiredArgument(
                    inspect.Parameter("text", inspect.Parameter.KEYWORD_ONLY, annotation=str)
                )

            text = ref.resolved.content

        async with ctx.typing():
            result = await self.translate_func(ctx, text, to, _from)

            if isinstance(result, discord.Embed):
                return await ctx.send(embed=result)

            if result == "TEXT_TOO_LARGE":
                return await ctx.send("Text is too large to translate.", ephemeral=True)
            elif result == "TO_LANG_INVALID":
                return await ctx.send(f"Language `{to}` not found.", ephemeral=True)
            elif result == "FROM_LANG_INVALID":
                return await ctx.send(f"Language `{_from}` not found.", ephemeral=True)
            else:
                return await ctx.send(f"An error occurred, please report this error: {result}")

    @translate.command(name="languages")
    async def translate_languages(self, ctx: Context, *, query: str = None):
        """
        Shows a list of languages that can be translated to.

        You can also search for specific languages e.g `yoda translate languages chinese` or `yoda translate languages eng`.
        """

        if query:
            async with ctx.typing():
                query = query.strip()

                lang = self.translate.get_language(query)

                if not lang:
                    return await ctx.send(f"Language `{query}` not found.", ephemeral=True)

                lang_code = lang["languageCode"]
                lang_name = lang["displayName"]

                embed = discord.Embed(color=self.bot.color)
                embed.title = lang_name

                embed.description = f"**Language Name:** {lang_name}\n**Language Code:** {lang_code}"

                return await ctx.send(embed=embed)

        source = TranslateLanguagesPaginator(self.translate.languages, per_page=10)
        menu = YodaMenuPages(source, delete_message_after=True)
        return await menu.start(ctx)

    async def translate_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        text = message.content

        from_lang = await self.translate.detect_language(text)
        from_lang = self.translate.get_language(from_lang["languageCode"])

        class Modal(discord.ui.Modal):
            _from = discord.ui.TextInput(
                label="Source Language",
                placeholder="Enter the language for the specific message sent",
                default=from_lang["displayName"],
                required=False,
            )
            to = discord.ui.TextInput(
                label="Destination Language",
                placeholder="Enter the language you want to " "translate to",
            )

            def __init__(self, *args, **kwargs):
                self.cls = kwargs.pop("translate")
                self.inter = kwargs.pop("interaction")
                super().__init__(*args, **kwargs)

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=True, thinking=True)

                ctx = await Context.from_interaction(self.inter)

                to = self.to.value
                _from = self._from.value

                result = await self.cls.translate_func(ctx, text, to, _from)

                if isinstance(result, discord.Embed):
                    return await interaction.followup.send(embed=result, ephemeral=True)

                if result == "TEXT_TOO_LARGE":
                    return await interaction.followup.send("Text is too large to translate.", ephemeral=True)
                elif result == "TO_LANG_INVALID":
                    return await interaction.followup.send(f"Language `{to}` not found.", ephemeral=True)
                elif result == "FROM_LANG_INVALID":
                    return await interaction.followup.send(f"Language `{_from}` not found.", ephemeral=True)
                else:
                    return await interaction.followup.send(f"An error occurred, please report this error: {result}")

        return await interaction.response.send_modal(Modal(title="Translate", translate=self, interaction=interaction))


async def setup(bot: commands.Bot):
    await bot.add_cog(Translate(bot))
