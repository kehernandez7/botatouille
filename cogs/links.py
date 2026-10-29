from __future__ import annotations

import logging
import re

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# Each pattern matches the start of a link whose embed doesn't work in Discord, and the
# replacement swaps in a site that serves a proper embed for the same path.
LINK_FIXERS = (
    (
        re.compile(r'https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/', re.I),
        'https://vxtwitter.com/',
    ),
    # Keep the vm./vt. subdomain on short links; the fixer mirrors it
    (re.compile(r'https?://(www\.|vm\.|vt\.)?tiktok\.com/', re.I), r'https://\1tnktok.com/'),
    (re.compile(r'https?://(?:www\.|old\.|new\.)?reddit\.com/', re.I), 'https://vxreddit.com/'),
)

MUGSHAWTYS_REACTIONS = (
    '<:buss:1387240721156669481>',
    '<:jail:1387240745433432155>',
    '<:kill:1387246285744242820>',
)
WEBHOOK_NAME = 'Botatouille'


def fix_links(content: str) -> str:
    for pattern, replacement in LINK_FIXERS:
        content = pattern.sub(replacement, content)
    return content


class Links(commands.Cog):
    """Reposts links whose embeds don't work in Discord with ones that do."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhooks: dict[int, discord.Webhook] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        fixed_content = fix_links(message.content)
        if fixed_content == message.content:
            return
        # Too big to re-upload, and deleting the original would lose them
        if sum(a.size for a in message.attachments) > message.guild.filesize_limit:
            return

        sent_message = await self.repost_as_author(message, fixed_content)
        if sent_message is None:
            sent_message = await self.repost_as_bot(message, fixed_content)
        await message.delete()

        if '/mugshawtys/' in message.content:
            for reaction in MUGSHAWTYS_REACTIONS:
                await sent_message.add_reaction(reaction)

    async def repost_as_author(
        self, message: discord.Message, content: str
    ) -> discord.Message | None:
        """Repost through a webhook so it shows the author's name and avatar.

        Returns None when the bot can't use a webhook in this channel.
        """
        channel = message.channel
        thread = channel if isinstance(channel, discord.Thread) else discord.utils.MISSING
        webhook_channel = channel.parent if thread else channel
        webhook = await self.get_webhook(webhook_channel)
        if webhook is None:
            return None

        # Webhooks can't send real replies, so link to the replied-to message instead
        if message.reference and message.reference.message_id:
            content = f'-# ↪ Replying to {message.reference.jump_url}\n{content}'

        try:
            return await webhook.send(
                content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                files=[await a.to_file() for a in message.attachments],
                thread=thread,
                allowed_mentions=discord.AllowedMentions.none(),
                wait=True,
            )
        except discord.HTTPException:
            log.warning('Webhook repost failed in #%s', channel, exc_info=True)
            # The webhook may have been deleted; look it up again next time
            self.webhooks.pop(webhook_channel.id, None)
            return None

    async def repost_as_bot(self, message: discord.Message, content: str) -> discord.Message:
        """Repost as the bot, tagging the author, as a reply if the original was one."""
        tagged_message = f'{message.author.mention} {content}'
        files = [await a.to_file() for a in message.attachments]
        replied_message = message.reference.resolved if message.reference else None
        if isinstance(replied_message, discord.Message):
            return await replied_message.reply(tagged_message, files=files)
        return await message.channel.send(tagged_message, files=files)

    async def get_webhook(self, channel: discord.abc.GuildChannel | None) -> discord.Webhook | None:
        """Find or create this bot's webhook for a channel, if it has permission to."""
        if channel is None or not hasattr(channel, 'webhooks'):
            return None
        if channel.id in self.webhooks:
            return self.webhooks[channel.id]
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            return None

        try:
            webhook = next(
                (w for w in await channel.webhooks() if w.user == self.bot.user and w.token),
                None,
            ) or await channel.create_webhook(name=WEBHOOK_NAME)
        except discord.HTTPException:
            log.warning('Could not get a webhook for #%s', channel, exc_info=True)
            return None

        self.webhooks[channel.id] = webhook
        return webhook


async def setup(bot: commands.Bot):
    await bot.add_cog(Links(bot))
