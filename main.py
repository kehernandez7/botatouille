import json
import os
import random
import re

import discord
from discord import app_commands
from discord.ext import commands
from sleeper.api import (
    get_league,
    get_matchups_for_week,
    get_rosters,
    get_users_in_league,
)
from keep_alive import keep_alive
from datetime import datetime, timedelta, timezone
from collections import defaultdict

bot = commands.Bot(
    command_prefix="/",
    case_insensitive=True,
    intents=discord.Intents.all()
)
client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)
bot.author_id = 1081353882367709314
food_data_api_key = os.getenv("FOOD_DATA_API_KEY")
LEAGUE_ID = "1257103807985229824"
SEASON_START_TUESDAY = datetime(2025, 9, 9, tzinfo=timezone.utc)  


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
    if 'www.x.com' in message.content:
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


@bot.tree.command(name="sleeper", description="Get weekly high score leaders from Sleeper")
async def sleeper(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        # 1. Figure out current week
        now = datetime.now(timezone.utc)
        weeks_passed = (now - SEASON_START_TUESDAY).days // 7 + 1
        current_week = max(1, weeks_passed)

        # 2. Get users & rosters
        users = get_users_in_league(league_id=LEAGUE_ID)
        rosters = get_rosters(league_id=LEAGUE_ID)

        # Map roster_id -> user display name
        roster_to_user = {}
        for r in rosters:
            user_id = r["owner_id"]
            user_info = next((u for u in users if u["user_id"] == user_id), None)
            if user_info:
                roster_to_user[r["roster_id"]] = user_info["display_name"]

        # 3. Count weekly wins
        weekly_wins = defaultdict(int)

        for week in range(1, current_week + 1):
            matchups = get_matchups_for_week(league_id=LEAGUE_ID, week=week)
            if not matchups:
                continue

            # Find highest points that week
            top_roster = max(matchups, key=lambda m: m["points"])
            top_user = roster_to_user.get(top_roster["roster_id"], "Unknown")
            weekly_wins[top_user] += 1

        # 4. Format leaderboard
        leaderboard = "\n".join(
            f"**{user}**: {wins} wins"
            for user, wins in sorted(weekly_wins.items(), key=lambda x: x[1], reverse=True)
        )

        if not leaderboard:
            leaderboard = "No data yet."

        await interaction.followup.send(f"🏆 Weekly High Score Leaders:\n{leaderboard}")

    except Exception as ex:
        print(ex)
        await interaction.followup.send("❌ Sorry, I couldn't fetch Sleeper data right now.")


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
