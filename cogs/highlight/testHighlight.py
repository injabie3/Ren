#!/usr/bin/env python3

import datetime
from collections import namedtuple
from copy import deepcopy

import pytest

from cogs.highlight import highlight

import discord

from redbot.pytest.core import *
from redbot.core import data_manager
from redbot.core.bot import Red
from redbot.core.cli import parse_cli_flags

@pytest.fixture()
def textChannelFactory(guild_factory):
    mockChannel = namedtuple("TextChannel", "id guild")
    class TextChannelFactory():
        def get(self):
            return mockChannel(1, guild_factory.get())
    return TextChannelFactory()

@pytest.fixture()
def messageFactory(textChannelFactory):
    mockMessage = namedtuple("Message", "id guild channel created_at content")
    class MessageFactory():

        def __init__(self):
            self.channel = textChannelFactory.get()
        
        def get(self, createdAt=datetime.datetime.now()):
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
async def testSomeBullshit(configureRed):
    pass
