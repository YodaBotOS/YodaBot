import discord
from discord.ext import commands

from core.openai import OpenAI


class ChatModal(discord.ui.Modal):
    text = discord.ui.TextInput(label="Text", placeholder="Enter your text to be sent to the AI")

    def __init__(self, *args, **kwargs):
        self.openai: OpenAI = kwargs.pop("openai")
        self.ephemeral: bool = kwargs.pop("ephemeral", False)
        self.view: discord.ui.View = kwargs.pop("view")
        self.prev_msg: discord.Message = kwargs.pop("prev_msg", None)
        self.is_google: bool = kwargs.pop("google", False)
        super().__init__(*args, **kwargs)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        text_prompt = self.text.value
        text_prompt = discord.utils.escape_markdown(text_prompt)

        try:
            text = await self.openai.reply(interaction, text_prompt)
        except Exception as e:
            return await interaction.followup.send(
                f"Something went wrong. Try again later.",
                view=self.view,
                ephemeral=True,
            )

        embed = discord.Embed(color=interaction.client.color)
        embed.set_author(name="GoogleGPT Chat:" if self.is_google else "Chat:", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Input/Prompt:", value=text_prompt, inline=False)
        embed.add_field(name="Output/Response:", value=text, inline=False)

        if self.prev_msg:
            await self.prev_msg.edit(view=None)

        return await interaction.followup.send(embed=embed, view=self.view, ephemeral=self.ephemeral)


class ChatView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        self.openai = kwargs.pop("openai")
        self.ephemeral = kwargs.pop("ephemeral", False)
        self.user = kwargs.pop("user")
        self.is_google = kwargs.pop("google", False)
        self.stopped = False
        self.prev_msg = None

        if "timeout" not in kwargs:
            kwargs["timeout"] = None

        super().__init__(*args, **kwargs)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(f"This chat doesn't belong to you.", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="Respond", style=discord.ButtonStyle.gray)
    async def respond_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.stopped:
            for i in self.children:
                i.disabled = True

            await interaction.message.edit(view=self)

            return self.stop()

        self.prev_msg = interaction.message

        return await interaction.response.send_modal(
            ChatModal(
                title="GoogleGPT Chat" if self.is_google else "Chat",
                openai=self.openai,
                view=self,
                ephemeral=self.ephemeral,
                prev_msg=self.prev_msg,
                google=self.is_google,
            )
        )

    @discord.ui.button(
        label="Stop",
        style=discord.ButtonStyle.red,
        emoji="<:StopButton:845592836116054017>",
    )
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for i in self.children:
            i.disabled = True

        self.stopped = True

        await interaction.message.edit(view=self)
        await interaction.response.send_message("Chat ended.", ephemeral=self.ephemeral)

        return self.stop()
