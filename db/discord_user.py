import datetime

import discord

from db import bot_db

users = bot_db['discord_users']


def create_or_update_user(discord_user: discord.user.User):
    existing_user = users.find_one({"user_id": discord_user.id})
    if existing_user is None:
        new_user = {
            "user_id": discord_user.id,
            "username": discord_user.name,
            "discriminator": discord_user.discriminator,
            "last_used": datetime.datetime.now()
        }
        users.insert_one(new_user)
        return new_user
    else:
        users.update_one({"_id": existing_user.get("_id")}, {"$set": {"last_used": datetime.datetime.now()}})
    return existing_user
