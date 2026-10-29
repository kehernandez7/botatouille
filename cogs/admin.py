import logging

from discord.ext import commands

log = logging.getLogger(__name__)


class Admin(commands.Cog):
    """Owner-only commands for managing the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        """Push the current slash commands to Discord. Run this after adding or changing one."""
        synced = await self.bot.tree.sync()
        log.info('Synced %d app commands', len(synced))
        await ctx.send(f'Synced {len(synced)} command(s).')


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
