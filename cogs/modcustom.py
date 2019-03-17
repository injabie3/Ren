from collections import deque, defaultdict
import os
import re
import logging
import asyncio
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils.chat_formatting import escape_mass_mentions, box
from cogs.utils.paginator import Pages # For making pages, requires the util!

def checkFolders():
    folders = ("data", "data/modcustom/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def checkFiles():
    plonkedPerms = {"users": [], "roles": []}
    overridePerms = {"users": [], "roles": []}

    files = {
        "plonked_perms.json"      : plonkedPerms,
        "override_perms.json"      : overridePerms
    }

    for filename, value in files.items():
        if not os.path.isfile("data/modcustom/{}".format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json("data/modcustom/{}".format(filename), value)


class ModCustom(object):
    """Custom mod tools for use outside of the standard Ren-bot Framework"""

    def __init__(self, bot):
        self.bot = bot
        self.overridePerms = dataIO.load_json("data/modcustom/override_perms.json")
        self.plonkedPerms = dataIO.load_json("data/modcustom/plonked_perms.json")

    def isPlonked(self, server, member): # note: message.server isnt needed
        if len([x for x in self.plonkedPerms["users"] if member.id == x ]) == 0:
            return False
        else:
            return True

    def hasPerms(self, server, member):
        perms = []
        overrides = [] # these roles have higher precedence than blacklist roles
        for role in member.roles:
            perms += [x for x in self.plonkedPerms["roles"] if x in role.name]
            overrides += [x for x in self.overridePerms["roles"] if x in role.name]

        if len(perms) == 0: # no blacklisted roles, we good to go
            return True
        elif len(perms) != 0 and len(overrides) != 0:
            # have a blacklisted role, but also have a whitelisted role, good to go
            return True
        else: # sorry, better luck next time
            return False

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def plonked(self, ctx):
        """Bans users/roles from using the bot.

        Any users/roles that are on a blacklist here will be UNABLE to use certain
        features of the bot, UNLESS they are on an override list as set using the
        [p]overridden command.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    # [p]plonked users
    @plonked.group(name="users", pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def userSettings(self, ctx):
        """Category: change settings for users."""
        if str(ctx.invoked_subcommand).lower() == "plonked users":
            await self.bot.send_cmd_help(ctx)

    # [p]plonked roles
    @plonked.group(name="roles", pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def roleSettings(self, ctx):
        """Category: change settings for roles."""
        if str(ctx.invoked_subcommand).lower() == "plonked roles":
            await self.bot.send_cmd_help(ctx)

    @userSettings.command(name="add")
    async def _blacklistAddUser(self, user: discord.Member):
        """Adds user to bot's blacklist"""
        if user.id not in self.plonkedPerms["users"]:
            self.plonkedPerms["users"].append(user.id)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonkedPerms)
            await self.bot.say("User has been added to blacklist.")
        else:
            await self.bot.say("User is already blacklisted.")

    @roleSettings.command(name="add")
    async def _blacklistAddRole(self, role: str):
        """Adds role to bot's blacklist"""
        if role not in self.plonkedPerms["roles"]:
            self.plonkedPerms["roles"].append(role)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonkedPerms)
            await self.bot.say("Role has been added to blacklist.")
        else:
            await self.bot.say("Role is already blacklisted.")

    @userSettings.command(name="del", aliases=["remove", "delete", "rm"])
    async def _blacklistRemoveUser(self, user: discord.Member):
        """Removes user from bot's blacklist"""
        if user.id in self.plonkedPerms["users"]:
            self.plonkedPerms["users"].remove(user.id)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonkedPerms)
            await self.bot.say("User has been removed from blacklist.")
        else:
            await self.bot.say("User is not in blacklist.")

    @roleSettings.command(name="del", aliases=["delete", "remove", "rm"])
    async def _blacklistRemoveRole(self, role: str):
        """Removes role from bot's blacklist"""
        if role in self.plonkedPerms["roles"]:
            self.plonkedPerms["roles"].remove(role)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonkedPerms)
            await self.bot.say("Role has been removed from blacklist.")
        else:
            await self.bot.say("Role is not in blacklist.")

    @userSettings.command(name="list", aliases=["ls"], pass_context=True)
    async def _blacklistListUsers(self, ctx):
        """List users on the bot's blacklist"""
        if not self.plonkedPerms["users"]:
            await self.bot.say("No users are on the blacklist.")
            return

        users = []
        for uid in self.plonkedPerms["users"]:
            userObj = ctx.message.server.get_member(uid)
            if not userObj:
                continue
            users.append(userObj.mention)

        page = Pages(self.bot, message=ctx.message, entries=users)
        page.embed.title = "Blacklisted users in **{}**".format(ctx.message.server.name)
        page.embed.colour = discord.Colour.red()
        await page.paginate()

    @roleSettings.command(name="list", aliases=["ls"], pass_context=True)
    async def _blacklistListRoles(self, ctx):
        """List roles on the bot's blacklist"""
        if not self.plonkedPerms["roles"]:
            await self.bot.say("No roles are on the blacklist.")
            return

        page = Pages(self.bot, message=ctx.message, entries=self.plonkedPerms["roles"])
        page.embed.title = "Blacklisted roles in **{}**".format(ctx.message.server.name)
        page.embed.colour = discord.Colour.red()
        await page.paginate()

    @plonked.command(name="clear")
    async def _blacklistClear(self):
        """Clears the blacklist"""
        self.plonkedPerms = {"users": [], "roles": []}
        dataIO.save_json("data/modcustom/plonked_perms.json", self.plonkedPerms)
        await self.bot.say("Blacklist is now empty.")

    @commands.group(pass_context=True)
    @checks.is_owner_or_permissions(administrator=True)
    async def overridden(self, ctx):
        """Allow certain users/roles to use the bot.

        Any users/roles that are on a whitelist here will be ABLE to use certain
        features of the bot, regardless of their status in the [p]plonked command.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    # [p]overridden users
    @overridden.group(name="users", pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def overriddenUserSettings(self, ctx):
        """Category: change settings for users."""
        if str(ctx.invoked_subcommand).lower() == "overridden users":
            await self.bot.send_cmd_help(ctx)

    # [p]overridden roles
    @overridden.group(name="roles", pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def overriddenRoleSettings(self, ctx):
        """Category: change settings for roles."""
        if str(ctx.invoked_subcommand).lower() == "overridden roles":
            await self.bot.send_cmd_help(ctx)

    @overriddenUserSettings.command(name="add")
    async def _whitelistAddUser(self, user: discord.Member):
        """Adds user to bot's whitelist"""
        if user.id not in self.overridePerms["users"]:
            if not self.overridePerms["users"]:
                msg = ("\nAll users not in whitelist will be ignored (owner, "
                       "admins and mods excluded)")
            else:
                msg = ""
            self.overridePerms["users"].append(user.id)
            dataIO.save_json("data/modcustom/override_perms.json", self.overridePerms)
            await self.bot.say("User has been added to whitelist." + msg)
        else:
            await self.bot.say("User is already whitelisted.")

    @overriddenRoleSettings.command(name="add")
    async def _whitelistAddRole(self, role: str):
        """Adds role to bot's whitelist"""
        if role not in self.overridePerms["roles"]:
            if not self.overridePerms["roles"]:
                msg = ("\nAll roles not in whitelist will be ignored (owner, "
                       "admins and mods excluded)")
            else:
                msg = ""
            self.overridePerms["roles"].append(role)
            dataIO.save_json("data/modcustom/override_perms.json", self.overridePerms)
            await self.bot.say("Role has been added to whitelist." + msg)
        else:
            await self.bot.say("Role is already whitelisted.")

    @overriddenUserSettings.command(name="delete", aliases=["remove", "del", "rm"])
    async def _whitelistRemoveUser(self, user: discord.Member):
        """Removes user from bot's whitelist"""
        if user.id in self.overridePerms["users"]:
            self.overridePerms["users"].remove(user.id)
            dataIO.save_json("data/modcustom/override_perms.json", self.overridePerms)
            await self.bot.say("User has been removed from whitelist.")
        else:
            await self.bot.say("User is not in whitelist.")

    @overriddenRoleSettings.command(name="delete", aliases=["remove", "del", "rm"])
    async def _whitelistRemoveRole(self, role: str):
        """Adds role to bot's whitelist"""
        if role in self.overridePerms["roles"]:
            self.overridePerms["roles"].remove(role)
            dataIO.save_json("data/modcustom/override_perms.json", self.overridePerms)
            await self.bot.say("Role has been removed from whitelist.")
        else:
            await self.bot.say("Role is not in whitelist.")

    @overriddenUserSettings.command(name="list", aliases=["ls"], pass_context=True)
    async def _whitelistListUsers(self, ctx):
        """List users on the bot's whitelist"""
        if not self.overridePerms["users"]:
            await self.bot.say("No users are on the whitelist.")
            return

        users = []
        for uid in self.overridePerms["users"]:
            userObj = ctx.message.server.get_member(uid)
            if not userObj:
                continue
            users.append(userObj.mention)

        page = Pages(self.bot, message=ctx.message, entries=users)
        page.embed.title = "Whitelisted users in **{}**".format(ctx.message.server.name)
        page.embed.colour = discord.Colour.red()
        await page.paginate()

    @overriddenRoleSettings.command(name="list", aliases=["ls"], pass_context=True)
    async def _whitelistListRoles(self, ctx):
        """List roles on the bot's whitelist"""
        if not self.overridePerms["roles"]:
            await self.bot.say("No roles are on the whitelist.")
            return

        page = Pages(self.bot, message=ctx.message, entries=self.overridePerms["roles"])
        page.embed.title = "Whitelisted roles in **{}**".format(ctx.message.server.name)
        page.embed.colour = discord.Colour.red()
        await page.paginate()

    @overridden.command(name="clear")
    async def _whitelistClear(self):
        """Clears the whitelist"""
        self.overridePerms = {"users": [], "roles": []}
        dataIO.save_json("data/modcustom/override_perms.json", self.overridePerms)
        await self.bot.say("Whitelist is now empty.")

def setup(bot):
    checkFolders()
    checkFiles()
    bot.add_cog(ModCustom(bot))
