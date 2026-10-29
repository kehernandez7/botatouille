import random

import discord
from discord import app_commands
from discord.ext import commands

MOCKING_EMOJI = '<:mockinbob:1387238863570997388>'
# Leaves room for the jump link within Discord's 2,000 character limit
MAX_MOCK_LENGTH = 1800


def to_mocking_text(text: str) -> str:
    """Alternate letter casing (starting randomly), leaving non-letters unchanged."""
    use_upper = random.choice([True, False])
    chars = []
    for char in text:
        if char.isalpha():
            chars.append(char.upper() if use_upper else char.lower())
            use_upper = not use_upper
        else:
            chars.append(char)
    return ''.join(chars)


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Context menus can't be declared with a decorator inside a cog, so register it here
        self.mock_menu = app_commands.ContextMenu(
            name='Mock this message', callback=self.mock_message
        )
        bot.tree.add_command(self.mock_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.mock_menu.name, type=self.mock_menu.type)

    @app_commands.command(name='mock', description='This command will mock a homie.')
    @app_commands.describe(prompt='name')
    async def mock(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.send_message(f'{to_mocking_text(prompt)} {MOCKING_EMOJI}')

    async def mock_message(self, interaction: discord.Interaction, message: discord.Message):
        if not message.content:
            await interaction.response.send_message(
                "There's no text in that message to mock.", ephemeral=True
            )
            return
        mocked = to_mocking_text(message.content[:MAX_MOCK_LENGTH])
        await interaction.response.send_message(
            f'{message.jump_url}\n{mocked} {MOCKING_EMOJI}',
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
