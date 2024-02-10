import discord
from discord import ui
from discord.ext import commands, menus

from core.context import Context


class YodaMenuPages(ui.View, menus.MenuPages):
    def __init__(
        self,
        source,
        *,
        delete_message_after=False,
        allow_other_users=False,
        ephemeral=False,
    ):
        super().__init__(timeout=None)
        self._source = source
        self.current_page = 0
        self.ctx: Context | discord.Interaction = None
        self.message = None
        self.delete_message_after = delete_message_after
        self.allow_other_users = allow_other_users
        self.ephemeral = ephemeral

    async def send_initial_message(self, ctx, channel):
        if isinstance(ctx, commands.Context):
            return await super().send_initial_message(ctx, channel)
        else:
            page = await self._source.get_page(0)
            kwargs = await self._get_kwargs_from_page(page)

            if ctx.response.is_done():
                return await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
                return await ctx.original_response()

    async def start(self, ctx, *, channel=None, wait=False):
        await self._source._prepare_once()
        self.ctx = ctx

        channel = channel or ctx

        self.message = await self.send_initial_message(ctx, channel)
        await self.update_buttons()

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if "view" not in value:
            value.update({"view": self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""

        original = (
            self.ctx.author if isinstance(self.ctx, commands.Context) else self.ctx.user
        )

        if not self.allow_other_users and interaction.user != original:
            await interaction.response.send_message(
                "This is not your interaction!", ephemeral=True
            )
            return False

        return True

    async def update_buttons(self, stopped: bool = False):
        if self.is_finished() or stopped:
            self.first_page.disabled = True
            self.before_page.disabled = True
            self.stop_page.disabled = True
            self.next_page.disabled = True
            self.last_page.disabled = True
            self.go_to_page.disabled = True
        else:
            self.first_page.disabled = False
            self.before_page.disabled = False
            self.stop_page.disabled = False
            self.next_page.disabled = False
            self.last_page.disabled = False
            self.go_to_page.disabled = False

            if self.current_page == 0:
                self.first_page.disabled = True
                self.before_page.disabled = True

            if self.current_page == (self._source.get_max_pages() - 1):
                self.next_page.disabled = True
                self.last_page.disabled = True

            self.stop_page.label = (
                f"Page {self.current_page + 1} of {self._source.get_max_pages()}"
            )

        await self.message.edit(view=self)

    @ui.button(
        emoji="<:doubleleft:943007192037068811>",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def first_page(self, interaction, button):
        await self.show_page(0)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(
        emoji="<:arrowleft:943007180389498891>",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def before_page(self, interaction, button):
        await self.show_checked_page(self.current_page - 1)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(
        emoji="<:StopButton:845592836116054017>",
        style=discord.ButtonStyle.danger,
        row=1,
    )
    async def stop_page(self, interaction, button):
        await interaction.response.defer()
        if self.delete_message_after:
            await self.message.delete(delay=0)
        else:
            await self.update_buttons(stopped=True)

        self.stop()

        await interaction.followup.send("Stopped.", ephemeral=True)

    @ui.button(
        emoji="<:arrowright:943007165734604820>",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def next_page(self, interaction, button):
        await self.show_checked_page(self.current_page + 1)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(
        emoji="<:doubleright:943007149917892658>",
        style=discord.ButtonStyle.blurple,
        row=1,
    )
    async def last_page(self, interaction, button):
        await self.show_page(self._source.get_max_pages() - 1)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(label="Go to page...", style=discord.ButtonStyle.gray, row=2)
    async def go_to_page(self, interaction, button):
        class Modal(ui.Modal, title="Go to page..."):
            def __init__(self, cls):
                self.cls = cls
                super().__init__(timeout=None)

            page_no = ui.TextInput(label="Page Number", placeholder="Enter page number")

            async def on_submit(self, interaction: discord.Interaction) -> None:
                try:
                    page = int(self.page_no.value)
                    await self.cls.show_page(page - 1)
                except ValueError:
                    await interaction.response.send_message(
                        f"Invalid page number. Try again.\nHint: Pick a page number from 1-{self.source.get_max_pages()}",
                        ephemeral=True,
                    )
                    return
                else:
                    await interaction.response.send_message(
                        f"Sure! Showing page {page}.", ephemeral=True
                    )

                await self.cls.update_buttons()

        await interaction.response.send_modal(Modal(self))
