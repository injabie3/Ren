"""YOURLS module.

"""
import json
from pathlib import Path

from redbot.core.bot import Red
from .yourlsCmd import YOURLS

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


def setup(bot: Red):
    """Add the cog to the bot."""
    yourlsCog = YOURLS(bot)
    bot.add_cog(yourlsCog)
