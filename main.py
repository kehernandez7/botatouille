import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

EXTENSIONS = ('cogs.admin', 'cogs.fun', 'cogs.links')
ERROR_MESSAGE = 'Something went wrong. Try again in a bit.'


class Botatouille(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', case_insensitive=True, intents=intents)
        self.tree.error(self.on_app_command_error)

    async def setup_hook(self):
        for extension in EXTENSIONS:
            await self.load_extension(extension)

    async def on_ready(self):
        log.info('Logged in as %s (ID: %s)', self.user, self.user.id)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # Ignore typos and non-owners poking at admin commands
        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return
        if isinstance(error, commands.UserInputError):
            await ctx.send(str(error))
            return
        log.error('Error in command %s', ctx.command, exc_info=error)
        await ctx.send(ERROR_MESSAGE)

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        log.error('Error in app command %s', interaction.command, exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(ERROR_MESSAGE, ephemeral=True)
        else:
            await interaction.response.send_message(ERROR_MESSAGE, ephemeral=True)


if __name__ == '__main__':
    Botatouille().run(os.environ['DISCORD_BOT_SECRET'], root_logger=True)
