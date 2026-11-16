"""Server Wrapped: a recap of what a server listens to on Spotify.

Nothing is logged until someone with Manage Server runs /wrapped start, and members can
opt out (which also deletes what was logged about them) at any time.

Listens come from the "Listening to Spotify" status Discord shows on members, so it only
sees members who have Spotify connected and shown on their Discord profile.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

DB_PATH = os.environ.get('WRAPPED_DB_PATH', 'wrapped.db')
# Spotify counts a stream after 30 seconds of listening, so do the same
MIN_LISTEN_SECONDS = 30
# A track starting over within this long of its end counts as a replay
REPLAY_SLACK_SECONDS = 5
TOP_COUNT = 5
# Keeps each recap field under Discord's 1,024 character limit
MAX_NAME_LENGTH = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracked_guilds (
    guild_id INTEGER PRIMARY KEY,
    started_at INTEGER NOT NULL,
    started_by INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS opted_out_users (
    user_id INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS listens (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    track_id TEXT NOT NULL,
    title TEXT NOT NULL,
    artists TEXT NOT NULL,
    main_artist TEXT NOT NULL,
    album TEXT NOT NULL,
    seconds INTEGER NOT NULL,
    listened_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS listens_by_guild_time ON listens (guild_id, listened_at);
CREATE INDEX IF NOT EXISTS listens_by_user ON listens (user_id);
"""

START_ANNOUNCEMENT = (
    "🎧 **Server Wrapped is on.** From now on I'll log what members of this server listen "
    'to on Spotify (the song, artist, album and how long you listened), using the '
    '"Listening to Spotify" status Discord already shows on your profile. '
    'Anyone can see the recap with `/wrapped recap`.\n\n'
    "Don't want to be included? Run `/wrapped optout` and I'll stop logging you and delete "
    'everything logged about you so far.'
)

PERIODS = {
    'month': 'This month',
    'year': 'This year',
    'all': 'All time',
}


def spotify_activity(member: discord.Member) -> discord.Spotify | None:
    return next((a for a in member.activities if isinstance(a, discord.Spotify)), None)


def finished_listen(
    before: discord.Spotify | None, after: discord.Spotify | None, now: datetime
) -> int | None:
    """If the track in `before` stopped playing, return how many seconds were heard.

    Returns None if it's still playing, including when someone seeks within it.
    """
    if before is None:
        return None
    if after is not None and after.track_id == before.track_id:
        # Same track again: a replay only if it restarted near the end
        replay_cutoff = before.end.timestamp() - REPLAY_SLACK_SECONDS
        if after.start.timestamp() < replay_cutoff:
            return None
        stopped_at = after.start
    else:
        stopped_at = now
    heard = min(stopped_at, before.end) - before.start
    return max(int(heard.total_seconds()), 0)


def period_start(period: str, now: datetime) -> int:
    if period == 'month':
        return int(datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp())
    if period == 'year':
        return int(datetime(now.year, 1, 1, tzinfo=timezone.utc).timestamp())
    return 0


def plural(count: int, word: str) -> str:
    return f'{count:,} {word}' if count == 1 else f'{count:,} {word}s'


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f'{hours:,}h {minutes}m'
    return f'{minutes}m'


def clean(name: str) -> str:
    """Shorten a song or artist name for the recap and escape its Markdown."""
    if len(name) > MAX_NAME_LENGTH:
        name = name[: MAX_NAME_LENGTH - 1] + '…'
    return discord.utils.escape_markdown(name)


class WrappedStore:
    """The SQLite database behind Server Wrapped.

    Every query is small, so they run directly on the event loop.
    """

    def __init__(self, path: str):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def tracked_guilds(self) -> dict[int, int]:
        """Return each tracked server's ID and when tracking started."""
        return dict(self.db.execute('SELECT guild_id, started_at FROM tracked_guilds'))

    def opted_out_users(self) -> set[int]:
        return {row[0] for row in self.db.execute('SELECT user_id FROM opted_out_users')}

    def start(self, guild_id: int, user_id: int, now: int):
        with self.db:
            self.db.execute(
                'INSERT OR IGNORE INTO tracked_guilds VALUES (?, ?, ?)', (guild_id, now, user_id)
            )

    def stop(self, guild_id: int, delete_data: bool) -> int:
        """Stop tracking a server. Returns how many listens were deleted."""
        with self.db:
            self.db.execute('DELETE FROM tracked_guilds WHERE guild_id = ?', (guild_id,))
            if not delete_data:
                return 0
            return self.db.execute('DELETE FROM listens WHERE guild_id = ?', (guild_id,)).rowcount

    def opt_out(self, user_id: int) -> int:
        """Stop tracking a user everywhere. Returns how many listens were deleted."""
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO opted_out_users VALUES (?)', (user_id,))
            return self.db.execute('DELETE FROM listens WHERE user_id = ?', (user_id,)).rowcount

    def opt_in(self, user_id: int):
        with self.db:
            self.db.execute('DELETE FROM opted_out_users WHERE user_id = ?', (user_id,))

    def add_listen(self, guild_id: int, user_id: int, track: discord.Spotify, seconds: int):
        with self.db:
            self.db.execute(
                'INSERT INTO listens (guild_id, user_id, track_id, title, artists, main_artist,'
                ' album, seconds, listened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    guild_id,
                    user_id,
                    track.track_id,
                    track.title,
                    ', '.join(track.artists),
                    track.artists[0] if track.artists else track.artist,
                    track.album,
                    seconds,
                    int(time.time()),
                ),
            )

    def user_listen_count(self, guild_id: int, user_id: int) -> int:
        return self.db.execute(
            'SELECT COUNT(*) FROM listens WHERE guild_id = ? AND user_id = ?', (guild_id, user_id)
        ).fetchone()[0]

    def recap(self, guild_id: int, since: int) -> dict | None:
        """Return the numbers for a recap, or None if nothing was logged in the period."""
        where = 'WHERE guild_id = ? AND listened_at >= ?'
        args = (guild_id, since)
        listens, seconds, listeners = self.db.execute(
            f'SELECT COUNT(*), SUM(seconds), COUNT(DISTINCT user_id) FROM listens {where}', args
        ).fetchone()
        if not listens:
            return None
        return {
            'listens': listens,
            'seconds': seconds,
            'listeners': listeners,
            'tracks': self.db.execute(
                f'SELECT title, artists, COUNT(*) AS plays, COUNT(DISTINCT user_id)'
                f' FROM listens {where} GROUP BY track_id ORDER BY plays DESC LIMIT ?',
                (*args, TOP_COUNT),
            ).fetchall(),
            'artists': self.db.execute(
                f'SELECT main_artist, COUNT(*) AS plays, SUM(seconds)'
                f' FROM listens {where} GROUP BY main_artist ORDER BY plays DESC LIMIT ?',
                (*args, TOP_COUNT),
            ).fetchall(),
            'listeners_by_time': self.db.execute(
                f'SELECT user_id, SUM(seconds) AS total, COUNT(*)'
                f' FROM listens {where} GROUP BY user_id ORDER BY total DESC LIMIT ?',
                (*args, TOP_COUNT),
            ).fetchall(),
            'on_repeat': self.db.execute(
                f'SELECT user_id, title, artists, COUNT(*) AS plays'
                f' FROM listens {where} GROUP BY user_id, track_id ORDER BY plays DESC LIMIT 1',
                args,
            ).fetchone(),
        }


def recap_embed(guild: discord.Guild, period: str, started_at: int | None, data: dict):
    embed = discord.Embed(
        title=f'🎧 {guild.name} Wrapped · {PERIODS[period]}',
        description=(
            f'**{plural(data["listens"], "listen")}** · **{format_duration(data["seconds"])}** '
            f'of music · **{plural(data["listeners"], "listener")}**'
        ),
        color=discord.Color.from_rgb(30, 215, 96),
    )

    embed.add_field(
        name='Top songs',
        value='\n'.join(
            f'{i}. **{clean(title)}** · {clean(artists)} '
            f'({plural(plays, "play")}, {plural(people, "listener")})'
            for i, (title, artists, plays, people) in enumerate(data['tracks'], 1)
        ),
        inline=False,
    )
    embed.add_field(
        name='Top artists',
        value='\n'.join(
            f'{i}. **{clean(artist)}** ({plural(plays, "play")}, {format_duration(seconds)})'
            for i, (artist, plays, seconds) in enumerate(data['artists'], 1)
        ),
        inline=False,
    )
    embed.add_field(
        name='Biggest listeners',
        value='\n'.join(
            f'{i}. <@{user_id}> · {format_duration(seconds)} ({plural(plays, "listen")})'
            for i, (user_id, seconds, plays) in enumerate(data['listeners_by_time'], 1)
        ),
        inline=False,
    )

    user_id, title, artists, plays = data['on_repeat']
    if plays > 1:
        embed.add_field(
            name='On repeat',
            value=(f'<@{user_id}> played **{clean(title)}** · {clean(artists)} {plays} times'),
            inline=False,
        )

    if started_at:
        embed.set_footer(text='Logging since')
        embed.timestamp = datetime.fromtimestamp(started_at, tz=timezone.utc)
    return embed


@app_commands.guild_only()
class Wrapped(commands.GroupCog, group_name='wrapped', group_description='Server Wrapped'):
    """A Spotify listening recap for the server, which admins have to turn on first."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = WrappedStore(DB_PATH)
        self.tracked = self.store.tracked_guilds()
        self.opted_out = self.store.opted_out_users()

    async def cog_unload(self):
        self.store.close()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if after.guild.id not in self.tracked or after.id in self.opted_out or after.bot:
            return
        previous = spotify_activity(before)
        seconds = finished_listen(previous, spotify_activity(after), discord.utils.utcnow())
        if seconds is not None and seconds >= MIN_LISTEN_SECONDS:
            self.store.add_listen(after.guild.id, after.id, previous, seconds)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # Don't keep anything about a server the bot is no longer in
        self.tracked.pop(guild.id, None)
        deleted = self.store.stop(guild.id, delete_data=True)
        log.info('Left %s; deleted %d Wrapped listens', guild, deleted)

    @app_commands.command(name='start', description='Start logging what members listen to')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def start(self, interaction: discord.Interaction):
        if interaction.guild_id in self.tracked:
            await interaction.response.send_message(
                'Server Wrapped is already on here.', ephemeral=True
            )
            return
        now = int(time.time())
        self.store.start(interaction.guild_id, interaction.user.id, now)
        self.tracked[interaction.guild_id] = now
        log.info('%s started Wrapped in %s', interaction.user, interaction.guild)
        # Public, so everyone knows logging started and how to opt out
        await interaction.response.send_message(START_ANNOUNCEMENT)

    @app_commands.command(name='stop', description='Stop logging what members listen to')
    @app_commands.describe(delete_data='Also delete everything logged so far')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stop(self, interaction: discord.Interaction, delete_data: bool = False):
        if interaction.guild_id not in self.tracked and not delete_data:
            await interaction.response.send_message("Server Wrapped isn't on here.", ephemeral=True)
            return
        self.tracked.pop(interaction.guild_id, None)
        deleted = self.store.stop(interaction.guild_id, delete_data)
        log.info('%s stopped Wrapped in %s', interaction.user, interaction.guild)
        message = "🎧 Server Wrapped is off. I've stopped logging what members listen to."
        if delete_data:
            message += f' I deleted {plural(deleted, "listen")} logged here.'
        else:
            message += ' What was logged so far is kept for `/wrapped recap`.'
        await interaction.response.send_message(message)

    @app_commands.command(name='optout', description='Stop logging what you listen to')
    async def optout(self, interaction: discord.Interaction):
        deleted = self.store.opt_out(interaction.user.id)
        self.opted_out.add(interaction.user.id)
        await interaction.response.send_message(
            f"You're opted out. I won't log what you listen to in any server, and I've deleted "
            f'the {plural(deleted, "listen")} I had for you. Run `/wrapped optin` to undo this.',
            ephemeral=True,
        )

    @app_commands.command(name='optin', description='Let Server Wrapped include you again')
    async def optin(self, interaction: discord.Interaction):
        if interaction.user.id not in self.opted_out:
            await interaction.response.send_message("You're not opted out.", ephemeral=True)
            return
        self.store.opt_in(interaction.user.id)
        self.opted_out.discard(interaction.user.id)
        await interaction.response.send_message(
            "You're opted back in. Servers with Wrapped turned on will log what you listen to.",
            ephemeral=True,
        )

    @app_commands.command(name='status', description='See whether Server Wrapped is logging you')
    async def status(self, interaction: discord.Interaction):
        started_at = self.tracked.get(interaction.guild_id)
        if started_at:
            lines = [f'Server Wrapped is **on** here, since <t:{started_at}:D>.']
        else:
            lines = ['Server Wrapped is **off** here, so nothing is being logged.']
        if interaction.user.id in self.opted_out:
            lines.append("You're **opted out**, so you're never logged.")
        else:
            count = self.store.user_listen_count(interaction.guild_id, interaction.user.id)
            lines.append(
                f"You're **opted in**. I have {plural(count, 'listen')} for you in this server. "
                'Run `/wrapped optout` to stop and delete them.'
            )
        await interaction.response.send_message('\n'.join(lines), ephemeral=True)

    @app_commands.command(name='recap', description="See what this server's been listening to")
    @app_commands.describe(period='Which stretch of time to recap (default: this month)')
    @app_commands.choices(
        period=[app_commands.Choice(name=name, value=key) for key, name in PERIODS.items()]
    )
    async def recap(
        self,
        interaction: discord.Interaction,
        period: str = 'month',
    ):
        period_key = period if period in PERIODS else 'month'
        since = period_start(period_key, discord.utils.utcnow())
        data = self.store.recap(interaction.guild_id, since)
        if data is None:
            if interaction.guild_id in self.tracked:
                message = 'Nothing logged for that stretch yet. Check back once people listen.'
            else:
                message = (
                    "Server Wrapped isn't on here. Someone with Manage Server can turn it on "
                    'with `/wrapped start`.'
                )
            await interaction.response.send_message(message, ephemeral=True)
            return
        embed = recap_embed(
            interaction.guild, period_key, self.tracked.get(interaction.guild_id), data
        )
        await interaction.response.send_message(
            embed=embed, allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Wrapped(bot))
