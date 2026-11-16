from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from urllib.parse import quote

import aiohttp
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

# Music links that Odesli (song.link) can match to the same song or album on other apps,
# keyed by the platform name Odesli uses
MUSIC_LINK_PATTERNS = (
    (
        'spotify',
        re.compile(r'https?://open\.spotify\.com/(?:intl-[\w-]+/)?(?:track|album)/\w+\S*', re.I),
    ),
    ('appleMusic', re.compile(r'https?://music\.apple\.com/\S+/(?:album|song)/\S+', re.I)),
    ('youtubeMusic', re.compile(r'https?://music\.youtube\.com/(?:watch|playlist)\?\S+', re.I)),
    (
        'tidal',
        re.compile(
            r'https?://(?:www\.|listen\.)?tidal\.com/(?:browse/)?(?:track|album)/\d+\S*', re.I
        ),
    ),
    (
        'deezer',
        re.compile(r'https?://(?:www\.)?deezer\.com/(?:[a-z]{2}/)?(?:track|album)/\d+\S*', re.I),
    ),
)
# Markdown and punctuation that often ends up stuck to the end of a pasted link
LINK_TRAILING_CHARS = '>)].,!?*|'
# The apps to show buttons for, in order, with their button labels
MUSIC_PLATFORMS = {
    'spotify': 'Spotify',
    'appleMusic': 'Apple Music',
    'youtubeMusic': 'YouTube Music',
    'youtube': 'YouTube',
    'tidal': 'Tidal',
    'deezer': 'Deezer',
    'amazonMusic': 'Amazon Music',
}
SONG_LINK_PAGE = 'https://song.link/'
ODESLI_API = 'https://api.song.link/v1-alpha.1/links'
# Odesli no longer answers requests without a key. Without one, the bot links to the
# song.link page, which lists the other apps, instead of a button for each app.
ODESLI_API_KEY = os.environ.get('ODESLI_API_KEY')
MUSIC_CACHE_SIZE = 500


def fix_links(content: str) -> str:
    for pattern, replacement in LINK_FIXERS:
        content = pattern.sub(replacement, content)
    return content


def find_music_link(content: str) -> tuple[str, str] | None:
    """Return the platform and URL of the first music link in a message, if any."""
    matches = [
        (match.start(), platform, match.group().rstrip(LINK_TRAILING_CHARS))
        for platform, pattern in MUSIC_LINK_PATTERNS
        if (match := pattern.search(content))
    ]
    if not matches:
        return None
    _, platform, url = min(matches)
    return platform, url


@dataclass
class MusicLinks:
    title: str | None
    artist: str | None
    # Platform name to URL, for the platforms in MUSIC_PLATFORMS that have the song
    links: dict[str, str]
    page_url: str


def parse_odesli_response(data: dict) -> MusicLinks:
    entity = data.get('entitiesByUniqueId', {}).get(data.get('entityUniqueId'), {})
    found = data.get('linksByPlatform', {})
    return MusicLinks(
        title=entity.get('title'),
        artist=entity.get('artistName'),
        links={p: found[p]['url'] for p in MUSIC_PLATFORMS if p in found and 'url' in found[p]},
        page_url=data['pageUrl'],
    )


def song_link_page(url: str) -> str:
    return SONG_LINK_PAGE + quote(url, safe='')


def music_links_reply(
    source_platform: str, music: MusicLinks | None, url: str
) -> tuple[str, discord.ui.View] | None:
    """Build the reply text and buttons, or None if there are no other apps to offer."""
    view = discord.ui.View()
    if music is None:
        view.add_item(discord.ui.Button(label='Open in other apps', url=song_link_page(url)))
        return '-# 🎵 Listen on other apps', view

    for platform, link in music.links.items():
        if platform != source_platform:
            view.add_item(discord.ui.Button(label=MUSIC_PLATFORMS[platform], url=link))
    if not view.children:
        return None
    view.add_item(discord.ui.Button(label='All apps', url=music.page_url))

    if music.title and music.artist:
        title = discord.utils.escape_markdown(music.title)
        artist = discord.utils.escape_markdown(music.artist)
        return f'-# 🎵 **{title}** by {artist} on other apps', view
    return '-# 🎵 Listen on other apps', view


class Links(commands.Cog):
    """Reposts links whose embeds don't work in Discord with ones that do, and adds links
    to other music apps under song links."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhooks: dict[int, discord.Webhook] = {}
        self.music_cache: dict[str, MusicLinks] = {}
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        reposted = await self.fix_message_links(message)
        music_link = find_music_link(message.content)
        if music_link:
            # The original is gone if it was reposted, so reply to the repost instead
            await self.reply_with_music_links(message.channel, reposted or message, *music_link)

    async def fix_message_links(self, message: discord.Message) -> discord.Message | None:
        """Repost the message with fixed links and delete the original.

        Returns the repost, or None if there was nothing to fix.
        """
        fixed_content = fix_links(message.content)
        if fixed_content == message.content:
            return None
        # Too big to re-upload, and deleting the original would lose them
        if sum(a.size for a in message.attachments) > message.guild.filesize_limit:
            return None

        sent_message = await self.repost_as_author(message, fixed_content)
        if sent_message is None:
            sent_message = await self.repost_as_bot(message, fixed_content)
        await message.delete()

        if '/mugshawtys/' in message.content:
            for reaction in MUGSHAWTYS_REACTIONS:
                await sent_message.add_reaction(reaction)
        return sent_message

    async def reply_with_music_links(
        self,
        channel: discord.abc.Messageable,
        message: discord.Message,
        source_platform: str,
        url: str,
    ):
        music = await self.lookup_music_links(url) if ODESLI_API_KEY else None
        reply = music_links_reply(source_platform, music, url)
        if reply is None:
            return
        content, view = reply
        await channel.send(
            content,
            view=view,
            reference=message.to_reference(fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def lookup_music_links(self, url: str) -> MusicLinks | None:
        """Ask Odesli for the same song on other apps. Returns None if the lookup fails."""
        if url in self.music_cache:
            return self.music_cache[url]
        params = {'url': url, 'songIfSingle': 'true', 'key': ODESLI_API_KEY}
        try:
            async with self.session.get(ODESLI_API, params=params) as response:
                if response.status != 200:
                    log.info('Odesli returned %s for %s', response.status, url)
                    return None
                music = parse_odesli_response(await response.json())
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError):
            log.warning('Odesli lookup failed for %s', url, exc_info=True)
            return None

        if len(self.music_cache) >= MUSIC_CACHE_SIZE:
            self.music_cache.pop(next(iter(self.music_cache)))
        self.music_cache[url] = music
        return music

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
