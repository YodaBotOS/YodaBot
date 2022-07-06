import discord
from discord import ui
from discord.ext import menus


class YodaMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source, *, delete_message_after=False):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None
        self.delete_message_after = delete_message_after

    async def start(self, ctx, *, channel=None, wait=False):
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, channel)
        await self.update_buttons()

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.ctx.author

    async def update_buttons(self):
        if self.is_finished():
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

            self.stop_page.label = f'Page {self.current_page + 1} of {self._source.get_max_pages()}'

        await self.message.edit(view=self)

    @ui.button(emoji='<:doubleleft:943007192037068811>', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction, button):
        await self.show_page(0)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(emoji='<:arrowleft:943007180389498891>', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction, button):
        await self.show_checked_page(self.current_page - 1)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(emoji='<:StopButton:845592836116054017>', style=discord.ButtonStyle.danger)
    async def stop_page(self, interaction, button):
        await interaction.response.defer()
        self.stop()
        if self.delete_message_after:
            await self.message.delete(delay=0)
        else:
            await self.update_buttons()

    @ui.button(emoji='<:arrowright:943007165734604820>', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, button):
        await self.show_checked_page(self.current_page + 1)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(emoji='<:doubleright:943007149917892658>', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction, button):
        await self.show_page(self._source.get_max_pages() - 1)
        await self.update_buttons()
        await interaction.response.defer()

    @ui.button(label='Go to page...', style=discord.ButtonStyle.gray)
    async def go_to_page(self, interaction, button):
        await interaction.send_message(
            embed=discord.Embed(
                description='Enter the page number you want to go to.',
                color=interaction.client.color
            )
        )

        msg = await interaction.client.wait_for('message', check=lambda m: m.author == interaction.user and \
                                          m.channel == interaction.channel)

        try:
            await msg.delete()
        except:
            pass

        try:
            page = int(msg.content)
            await self.show_page(page - 1)
        except ValueError:
            await interaction.send_message('Invalid page number. Try again.')
            return

        await self.update_buttons()

        await interaction.response.defer()