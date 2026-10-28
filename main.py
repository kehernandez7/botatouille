import os
import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from keep_alive import keep_alive

# Matches x.com links (with or without www) so they can be swapped for vxtwitter embeds
X_LINK_PATTERN = re.compile(r'https?://(?:www\.)?x\.com/', re.IGNORECASE)
VXTWITTER_PREFIX = 'https://vxtwitter.com/'

MUGSHAWTYS_REACTIONS = (
    '<:buss:1387240721156669481>',
    '<:jail:1387240745433432155>',
    '<:kill:1387246285744242820>',
)
MOCKING_EMOJI = '<:mockinbob:1387238863570997388>'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', case_insensitive=True, intents=intents)


@bot.event
async def on_ready():
    print(f"I'm in as {bot.user}")
    await bot.tree.sync()


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user or not X_LINK_PATTERN.search(message.content):
        return
    await repost_with_vxtwitter(message)


async def repost_with_vxtwitter(message: discord.Message):
    """Delete the original message and repost it with x.com links rewritten to vxtwitter.com."""
    replied_message = message.reference.resolved if message.reference else None
    content = X_LINK_PATTERN.sub(VXTWITTER_PREFIX, message.content)
    tagged_message = f'{message.author.mention} {content}'

    await message.delete()

    if isinstance(replied_message, discord.Message):
        sent_message = await replied_message.reply(tagged_message)
    else:
        sent_message = await message.channel.send(tagged_message)

    if '/mugshawtys/' in message.content:
        for reaction in MUGSHAWTYS_REACTIONS:
            await sent_message.add_reaction(reaction)


@bot.tree.command(name='mock', description='This command will mock a homie.')
@app_commands.describe(prompt='name')
async def mock(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message(f'{to_mocking_text(prompt)} {MOCKING_EMOJI}')


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


if __name__ == '__main__':
    keep_alive()
    bot.run(os.environ['DISCORD_BOT_SECRET'])
