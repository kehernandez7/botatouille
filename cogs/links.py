import re

import discord
from discord.ext import commands

# Matches x.com links (with or without www) so they can be swapped for vxtwitter embeds
X_LINK_PATTERN = re.compile(r'https?://(?:www\.)?x\.com/', re.IGNORECASE)
VXTWITTER_PREFIX = 'https://vxtwitter.com/'

MUGSHAWTYS_REACTIONS = (
    '<:buss:1387240721156669481>',
    '<:jail:1387240745433432155>',
    '<:kill:1387246285744242820>',
)


class Links(commands.Cog):
    """Reposts links whose embeds don't work in Discord with ones that do."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user or not X_LINK_PATTERN.search(message.content):
            return
        await self.repost_with_vxtwitter(message)

    async def repost_with_vxtwitter(self, message: discord.Message):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Links(bot))
