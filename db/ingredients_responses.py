import datetime

import discord

from db import bot_db

ingredient_responses = bot_db['discord_ingredient_responses']


def insert_ingredient_response(interaction: discord.Interaction, prompt: str, response: str):
    new_record = {
        "discord_user_id": interaction.user.id,
        "prompt": prompt,
        "response": response,
        "timestamp": datetime.datetime.now()
    }
    ingredient_responses.insert_one(new_record)
