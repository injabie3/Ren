#!/usr/bin/env python3

import datetime
from collections import namedtuple
from copy import deepcopy

import discord
import pytest

from . import highlight

from redbot.pytest.core import *
from redbot.core import data_manager
from redbot.core.bot import Red
from redbot.core.cli import parse_cli_flags


# TODO move fixtures to testlib
@pytest.fixture()
def textChannelFactory(guild_factory):
    mockChannel = namedtuple("TextChannel", "id guild")

    class TextChannelFactory:
        def get(self, channelId=1):
            return mockChannel(channelId, guild_factory.get())

    return TextChannelFactory()


@pytest.fixture()
def messageFactory(textChannelFactory):
    mockMessage = namedtuple("Message", "id guild channel created_at content")

    class MessageFactory:
        def __init__(self):
            self.channelId = 1
            self.channel = textChannelFactory.get(channelId=self.channelId)

        def get(self, channelId=1, createdAt=datetime.datetime.now()):
            if self.channelId != self.channel.id:
                self.channel = textChannelFactory.get(channelId=self.channelId)
            return mockMessage(1, self.channel.guild, self.channel, createdAt, "Empty")

    return MessageFactory()


@pytest.fixture()
def configureRed():
    cliFlags = parse_cli_flags(["Rin"])
    cliFlags.instance_name = "temporary_red"
    data_manager.create_temp_config()
    data_manager.load_basic_configuration(cliFlags.instance_name)
    description = "Red test"
    red = Red(cli_flags=cliFlags, description="Red V3", dm_help=None)


# Tests
@pytest.mark.asyncio
async def testTriggeredUpdate(configureRed, messageFactory):
    hlCog = highlight.Highlight(red)
    firstTime = True
    for userId in [1111, 2222, 3333, 4444]:
        msgFactory = messageFactory
        message = msgFactory.get()

        createdAt = deepcopy(message.created_at)
        guild = message.guild
        channel = message.channel

        if firstTime:
            assert guild.id not in hlCog.lastTriggered.keys()
        hlCog._triggeredUpdate(message, userId)
        # Make sure the keys are updated appropriately
        assert guild.id in hlCog.lastTriggered.keys()
        assert channel.id in hlCog.lastTriggered[guild.id].keys()
        assert userId in hlCog.lastTriggered[guild.id][channel.id].keys()
        assert createdAt == hlCog.lastTriggered[guild.id][channel.id][userId]

        newTime = datetime.datetime.now() + datetime.timedelta(seconds=5)
        newMessage = msgFactory.get(createdAt=newTime)
        assert newMessage.channel.id == channel.id
        assert newMessage.guild.id == guild.id

        hlCog._triggeredUpdate(newMessage, userId)
        assert createdAt != hlCog.lastTriggered[guild.id][channel.id][userId]
        assert newMessage.created_at == hlCog.lastTriggered[guild.id][channel.id][userId]

        firstTime = False


@pytest.mark.asyncio
async def testTriggeredRecently(configureRed, messageFactory):
    hlCog = highlight.Highlight(red)
    triggeredUserId = 1111
    notTriggeredUserId = 2222
    timeout = 5

    msgFactory = messageFactory
    message1 = msgFactory.get()
    newTime = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    # This next message is in same guild, channel, but with an updated timestamp
    message2 = msgFactory.get(createdAt=newTime)
    # This next message is in the same guild, different channel
    msgFactory.channelId = 2
    message3 = msgFactory.get()

    createdAt = deepcopy(message1.created_at)

    guild = message1.guild
    channel = message1.channel

    # Sanity checks
    assert message1.guild == message2.guild

    hlCog._triggeredUpdate(message1, triggeredUserId)
    assert hlCog._triggeredRecently(message1, triggeredUserId)
    assert hlCog._triggeredRecently(message2, triggeredUserId, timeout=timeout + 1)
    assert not hlCog._triggeredRecently(message2, triggeredUserId, timeout=timeout)
    assert not hlCog._triggeredRecently(message2, notTriggeredUserId)

    for seconds in range(0, 100):
        # Test a range of timeout values to make sure different channel IDs report not
        # triggered recently
        assert not hlCog._triggeredRecently(message3, triggeredUserId, timeout=seconds)
        assert not hlCog._triggeredRecently(message3, notTriggeredUserId, timeout=seconds)
