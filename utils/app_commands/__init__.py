import traceback

import discord
import sentry_sdk
from discord import app_commands


class CommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: Exception, /):
        if isinstance(error, tuple):
            send_msg = error[1]
            error = error[0]
        else:
            send_msg = True

        if send_msg:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Error: {error}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Error: {error}", ephemeral=True)
            except:
                await interaction.followup.send(f"Error: {error}", ephemeral=True)

        # try:
        #     await interaction.response.defer()
        # except:
        #     pass
        #
        # try:
        #     await interaction.response.send_message(f"Error, please report: {error}", ephemeral=True)
        # except:
        #     await interaction.followup.send(f"Error, please report: {error}", ephemeral=True)

        traceback.print_exception(error)
        
        if interaction.command:
            command_name = interaction.command.name
        else:
            command_name = "not-a-command"

        with sentry_sdk.push_scope() as scope:
            scope.set_user({"username": str(interaction.user), "id": interaction.user.id})
            scope.set_tag("command-type", f"interaction")
            scope.set_tag("interaction-type", interaction.type.name.replace("_", "-"))
            scope.set_extra("command", command_name)

            sentry_sdk.capture_exception(error, scope=scope)
