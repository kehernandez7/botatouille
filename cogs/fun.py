import random

import discord
from discord import app_commands
from discord.ext import commands

MOCKING_EMOJI = '<:mockinbob:1387238863570997388>'


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

    @app_commands.command(name='mock', description='This command will mock a homie.')
    @app_commands.describe(prompt='name')
    async def mock(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.send_message(f'{to_mocking_text(prompt)} {MOCKING_EMOJI}')


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
