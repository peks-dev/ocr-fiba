"""
Built-in validation plugins.

Importing this module registers all built-in plugins in the global registry.
This should be imported once at application startup.
"""
from ..registry import register

# Core — extraction consistency (always relevant)
from .core import (
    QuarterSumsPlugin,
    DuplicateNumbersPlugin,
    GhostPlayersPlugin,
    ProgressiveVsFinalPlugin,
    PlayerVsProgressivePlugin,
    ProgressiveSequencePlugin,
    EntryAndFoulsConsistencyPlugin,
    IllegibleMarksPlugin,
)

register(QuarterSumsPlugin())
register(DuplicateNumbersPlugin())
register(GhostPlayersPlugin())
register(ProgressiveVsFinalPlugin())
register(PlayerVsProgressivePlugin())
register(ProgressiveSequencePlugin())
register(EntryAndFoulsConsistencyPlugin())
register(IllegibleMarksPlugin())

# FIBA sport rules
from .fiba_rules import PlayerFoulsPlugin, TeamFoulsPlugin

register(PlayerFoulsPlugin())
register(TeamFoulsPlugin())

# Referee use case
from .referee import PlayerPointsSumPlugin, WinnerConsistencyPlugin

register(PlayerPointsSumPlugin())
register(WinnerConsistencyPlugin())
