"""Interactive menu system for Agent Management Suite."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.colors import Colors
from menu.base import BaseMenu

__all__ = [
    "Colors",
    "BaseMenu",
]

# Lazy imports to avoid circular dependencies
def get_main_menu():
    from menu.main_menu import MainMenu
    return MainMenu

def get_agent_manager():
    from menu.agent_manager import AgentManager
    return AgentManager

def get_skill_browser():
    from menu.skill_browser import SkillBrowser
    return SkillBrowser

def get_plugin_browser():
    from menu.plugin_browser import PluginBrowser
    return PluginBrowser

def get_command_browser():
    from menu.command_browser import CommandBrowser
    return CommandBrowser

def get_hook_browser():
    from menu.hook_browser import HookBrowser
    return HookBrowser

def get_sync_menu():
    from menu.sync_menu import SyncMenu
    return SyncMenu
