"""Main menu for Agent Management Suite."""

from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu


class MainMenu(BaseMenu):
    """Main menu screen with all top-level options."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.syncer.load_all_claude()

    def run(self) -> Optional[str]:
        """Run the main menu loop."""
        while True:
            self.clear_screen()
            self._draw_menu()

            choice = self.prompt()

            if choice == '1':
                from .agent_manager import AgentManager
                AgentManager(self.syncer).run()
            elif choice == '2':
                from .skill_browser import SkillBrowser
                SkillBrowser(self.syncer).run()
            elif choice == '3':
                from .plugin_browser import PluginBrowser
                PluginBrowser(self.syncer).run()
            elif choice == '4':
                from .command_browser import CommandBrowser
                CommandBrowser(self.syncer).run()
            elif choice == '5':
                from .hook_browser import HookBrowser
                HookBrowser(self.syncer).run()
            elif choice == '6':
                from .sync_menu import SyncMenu
                SyncMenu(self.syncer).run()
            elif choice == '7':
                self._show_platform_status()
            elif choice in ('8', 'q', 'quit', 'exit'):
                return None
            else:
                self.print_error("Invalid choice")
                self.wait_for_key()

    def _draw_menu(self) -> None:
        """Draw the main menu."""
        c = self.colors

        self.draw_box("AGENT MANAGEMENT & SYNC SUITE")

        # Show summary counts
        agent_count = len(self.syncer.agents)
        skill_count = len(self.syncer.skills)
        plugin_count = len(self.syncer.plugins)
        command_count = len(self.syncer.commands)
        hook_count = len(self.syncer.hooks)

        summary = f"  {c.colorize(str(agent_count), c.CYAN)} agents | "
        summary += f"{c.colorize(str(skill_count), c.CYAN)} skills | "
        summary += f"{c.colorize(str(plugin_count), c.CYAN)} plugins"
        print(summary)
        print()

        # Main options
        self.draw_option("1", "Agent Manager", f"Browse, edit, and analyze {agent_count} agents")
        print()
        self.draw_option("2", "Skill Browser & Builder", f"Manage {skill_count} skills")
        print()
        self.draw_option("3", "Plugin Browser & Builder", f"Explore {plugin_count} plugins")
        print()
        self.draw_option("4", "Command Browser & Builder", f"View {command_count} commands")
        print()
        self.draw_option("5", "Hook Browser & Builder", f"Configure {hook_count} hooks")
        print()
        self.draw_option("6", "Sync to Platforms", "Export to other AI coding tools")
        print()
        self.draw_option("7", "Platform Status", "Check installation status")
        print()
        self.draw_option("8", "Exit")

    def _show_platform_status(self) -> None:
        """Display platform installation status."""
        from pathlib import Path

        self.clear_screen()
        self.draw_box("PLATFORM STATUS")

        home = Path.home()

        self.draw_section("SKILL.md Compatible:")

        platforms = [
            ("Codex CLI", home / ".codex", self._count_skills(home / ".codex" / "skills")),
            ("Gemini CLI", home / ".gemini", self._count_skills(home / ".gemini" / "skills")),
            ("Antigravity", home / ".gemini" / "antigravity", self._count_skills(home / ".gemini" / "antigravity" / "skills")),
            ("Continue", home / ".continue", self._count_skills(home / ".continue" / "skills")),
            ("OpenCode", home / ".opencode", self._count_skills(home / ".opencode" / "skills")),
            ("Trae", home / ".trae", self._count_skills(home / ".trae" / "skills")),
        ]

        for name, path, skill_count in platforms:
            exists = path.exists()
            detail = f"{skill_count} skills synced" if exists and skill_count > 0 else ""
            self.draw_status(name, exists, detail)

        self.draw_section("Requires Conversion:")

        other_platforms = [
            ("Cursor", home / ".cursor"),
            ("Windsurf", home / ".windsurf"),
            ("Roo Code", home / ".roo"),
            ("Kiro", home / ".kiro"),
            ("GitHub Copilot", home / ".github"),
            ("Aider", home / ".aider.conf.yml"),
        ]

        for name, path in other_platforms:
            self.draw_status(name, path.exists())

        self.wait_for_key()

    def _count_skills(self, path) -> int:
        """Count skills in a directory."""
        if not path.exists():
            return 0
        return sum(1 for d in path.iterdir() if d.is_dir() and (d / "SKILL.md").exists())
