import json
import os
import random
import re

import discord
from discord import app_commands
from discord.ext import commands

from keep_alive import keep_alive

bot = commands.Bot(
    command_prefix="/",
    case_insensitive=True,
    intents=discord.Intents.all()
)
client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)
bot.author_id = os.getenv("BOT_AUTHOR_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
food_data_api_key = os.getenv("FOOD_DATA_API_KEY")


@bot.event
async def on_ready():
    print("I'm in")
    print(bot.user)
    await bot.tree.sync()

@bot.event
async def on_message(message):
    # Prevent responding to itself
    if message.author == bot.user:
        return

    # Skip if message has no content
    if not message.content:
        return

    # Skip if already using the alternate domains
    if 'vxtwitter.com' in message.content or 'ddinstagram.com' in message.content:
        return

    # Determine if the message is a reply
    replied_message = None
    if message.reference and isinstance(message.reference.resolved, discord.Message):
        replied_message = message.reference.resolved

    # Define your replacements
    updated = None
    if 'instagram.com' in message.content:
        updated = replace_domain_text(message.content, 'instagram.com', 'ddinstagram.com')
    elif 'www.x.com' in message.content:
        await send_tweet(message, replied_message)
        updated = replace_domain_text(message.content, 'x.com', 'vxtwitter.com')
    elif 'https://x.com' in message.content:
        await send_tweet(message, replied_message)
    elif 'open.spotify.com' in message.content:
        updated = replace_domain_text(message.content, 'open.spotify.com', 'player.spotify.com')

    # If there’s a modified message, handle it
    if updated:
        tagged_message = f"{message.author.mention} {updated}"
        await message.delete()
        if replied_message:
            await replied_message.reply(tagged_message)
        else:
            await message.channel.send(tagged_message)


def replace_domain_text(content, domain, replacement_text):
    # Replace the domain with the specified replacement text
    replaced_message = content.replace(domain, replacement_text)
    return replaced_message


async def send_tweet(message, replied_message):
    replaced_message = replace_domain_text(message.content, 'x.com', 'vxtwitter.com')
    tagged_message = f"{message.author.mention} {replaced_message}"

    await message.delete()

    # Send the updated message
    if replied_message:
        sent_msg = await replied_message.reply(tagged_message)
    else:
        sent_msg = await message.channel.send(tagged_message)

    # Check if a specific username is in the URL
    if '/mugshawtys/' in message.content:
        await sent_msg.add_reaction('<:buss:1387240721156669481>')
        await sent_msg.add_reaction('<:jail:1387240745433432155>')
        await sent_msg.add_reaction('<:kill:1387246285744242820>')


@bot.tree.command(name='mock', description='This command will mock a homie.')
@app_commands.describe(prompt='name')
async def mockMessage(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    mock = to_mocking_text(prompt)
    try:
        await interaction.followup.send(f"{mock} <:mockinbob:1387238863570997388>", wait=True)
    except Exception as ex:
        print(ex)
        await interaction.followup.send('Sorry, I am unable to mock your homie at this time.')


def to_mocking_text(text):
    result = ''
    use_upper = random.choice([True, False])  # Random start for variety
    for char in text:
        if char.isalpha():
            result += char.upper() if use_upper else char.lower()
            use_upper = not use_upper
        else:
            result += char  # Keep punctuation/spaces unchanged
    return result

extensions = [
    'cogs.cog_example'
]

if __name__ == '__main__':
    for extension in extensions:
        bot.load_extension(extension)

keep_alive()
token = os.environ.get("DISCORD_BOT_SECRET")
bot.run(token)
