"""Stats module.

Collect some stats for ourselves.
"""

from datetime import datetime
import logging
import discord
from redbot.core import Config, checks, commands, data_manager
from redbot.core.bot import Red
from redbot.core.commands.context import Context
from redbot.core.utils import paginator

BASE_MEMBER = \
{
    "messageCount": {}, # Total number of messages sent, per channel basis.
    "reactCount": {}, # Total number of reactions made, per channel basis.
    "serverJoinLeave": {} # key: time since epoch; value: join/leave
}

BASE_GUILD = \
{
    "initialized": False,
}

BASE_CHANNEL = \
{
    "lastUpdated": None
}


class Stats(commands.Cog):
    """A cog to collect statistics within a guild."""
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self,
                                      identifier=5842647,
                                      force_registration=True)
        self.config.register_member(**BASE_MEMBER)
        self.config.register_channel(**BASE_CHANNEL)
        self.config.register_guild(**BASE_GUILD)

        # Initialize logger, and save to cog folder.
        saveFolder = data_manager.cog_data_path(cog_instance=self)
        self.logger = logging.getLogger("red.Stats")
        if self.logger.level == 0:
            # Prevents the self.logger from being loaded again in case of module reload.
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(filename=str(saveFolder) +
                                          "/info.log",
                                          encoding="utf-8",
                                          mode="a")
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(message)s",
                                  datefmt="[%d/%m/%Y %H:%M:%S]"))
            self.logger.addHandler(handler)


    @commands.group(name="stats")
    @commands.guild_only()
    async def statsGroup(self, ctx: Context):
        """Stats for the guild."""
        pass

    @statsGroup.command(name="update")
    async def update(self, ctx: Context):
        """Update the message count for all users on the guild.

        This operation may take a long time.
        """
        self.logger.debug("Starting stats update on guild %s (%s)",
                          ctx.guild.name, ctx.guild.id)
        status = await ctx.send(":information_source: Updating, please wait...")
        membersLock = self.config.get_members_lock(ctx.guild)
        channelsLock = self.config.get_channels_lock()

        # TODO double check to make sure that we can't deadlock here.
        await membersLock.acquire()
        await channelsLock.acquire()

        self.logger.debug("Member and channel locks acquired")

        for chan in ctx.guild.text_channels:
            self.logger.debug("Processing channel %s (%s)", chan.name, chan.id)
            await status.edit(content=":information_source: Processing channel **{}"
                              "**".format(chan.name))
            lastUpdated = await self.config.channel(chan).lastUpdated()
            lastUpdated = datetime.fromtimestamp(lastUpdated) if lastUpdated else None
            try:
                async for msg in chan.history(limit=None, after=lastUpdated,
                        oldest_first=True):
                    self.logger.debug("Current message: %s", msg)
                    await self.config.channel(chan).lastUpdated.set(msg.created_at.
                            timestamp())
                    self._updateMessageCount(msg)
            except discord.Forbidden:
                self.logger.error("Permission error! Check traceback", exc_info=True)

        await status.edit(content=":white_check_mark: Stats update complete!")

    @statsGroup.command(name="info")
    async def info(self, ctx: Context, member: discord.Member=None):
        """Check user info.

        Parameters:
        -----------
        member: discord.Member (optional)
            The guild member you wish to check info for. If not specified, this defaults
            to you.
        """
        total = 0
        if not member:
            member = ctx.author
        memberData = await self.config.member(member).messageCount()

        for chanId, msgs in memberData.items():
            total += msgs
        await ctx.send("You have sent {} messages on this server!".format(total))

    async def _updateMessageCount(self, msg: discord.Message):
        """Update message count for a guild member.

        This will +1 the current message count for the user.

        Parameters:
        -----------
        msg: discord.Message
            The message you want to use to update.
        """
        if msg.author.bot or not isinstance(msg.author, discord.Member):
            return
        async with self.config.member(msg.author).messageCount() as msgCount:
            if str(msg.channel.id) not in msgCount.keys():
                msgCount[str(msg.channel.id)] = 1
            else:
                msgCount[str(msg.channel.id)] += 1

    async def _updateServerJoinLeave(self, timestamp: datetime, status: str):
        """Update server join/leave status.

        Parameters:
        -----------
        timestamp: datetime.datetime
            The time when this status change occurred.
        status: str
            One of either "join" or "leave".

        Raises:
        -------
        ValueError
            The provided status was invalid.
        """
        if status != "join" and status != "leave":
            raise ValueError("Status should be one of 'join' or 'leave'")

        time

    @commands.Cog.listener("on_message")
    async def messageListener(self, msg: discord.Message):
        """Check each message and update the info for the guild member."""
        await self._updateMessageCount(msg)
        await self.config.channel(msg).lastUpdated.set(msg.created_at.timestamp())
