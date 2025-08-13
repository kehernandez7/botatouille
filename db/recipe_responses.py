import datetime

import discord

from db import bot_db

recipe_responses = bot_db['discord_recipe_responses']


def insert_recipe_response(interaction: discord.Interaction, prompt: str, response: str):
    new_record = {
        "discord_user_id": interaction.user.id,
        "prompt": prompt,
        "response": response,
        "timestamp": datetime.datetime.now()
    }
    recipe_responses.insert_one(new_record)
