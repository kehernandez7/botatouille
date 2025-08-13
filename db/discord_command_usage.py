import datetime

import discord

from db import bot_db

command_usage = bot_db['discord_command_usage']


def insert_new_usage(interaction: discord.Interaction, command: str, usage: str):
    new_record = {
        "discord_user_id": interaction.user.id,
        "command_name": command,
        "command_usage": usage,
        "timestamp": datetime.datetime.now()
    }
    command_usage.insert_one(new_record)
