import datetime

import discord

from db import bot_db

art_responses = bot_db['discord_art_responses']


def insert_art_response(interaction: discord.Interaction, prompt: str, filename: str, variation: int):
    new_record = {
        "discord_user_id": interaction.user.id,
        "prompt": prompt,
        "filename": filename,
        "prompt_variation": variation,
        "timestamp": datetime.datetime.now()
    }
    art_responses.insert_one(new_record)
