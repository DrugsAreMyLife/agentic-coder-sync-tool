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
                from .workflow_menu import WorkflowMenu
                WorkflowMenu(self.syncer).run()
            elif choice == '8':
                from .exclusion_menu import ExclusionMenu
                ExclusionMenu(self.syncer).run()
            elif choice.lower() == 'c':
                from .compat_menu import CompatMenu
                CompatMenu(self.syncer).run()
            elif choice.lower() == 'p':
                self._show_platform_status()
            elif choice.lower() == 'e':
                self._export_bundle()
            elif choice.lower() == 'i':
                self._import_bundle()
            elif choice in ('0', 'q', 'quit', 'exit'):
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

        # Component browsers
        self.draw_section("Component Browsers:")
        self.draw_option("1", "Agent Manager", f"Browse, edit, and analyze {agent_count} agents")
        self.draw_option("2", "Skill Browser", f"Manage {skill_count} skills")
        self.draw_option("3", "Plugin Browser", f"Explore {plugin_count} plugins")
        self.draw_option("4", "Command Browser", f"View {command_count} commands")
        self.draw_option("5", "Hook Browser", f"Configure {hook_count} hooks")

        # Orchestration & Sync
        self.draw_section("Orchestration & Sync:")
        self.draw_option("6", "Sync to Platforms", "Export to other AI coding tools")
        self.draw_option("7", "Workflow Designer", "Design agent handoff workflows")
        self.draw_option("8", "Exclusion Manager", "Mark private/excluded components")

        # Utilities
        self.draw_section("Utilities:")
        self.draw_option("C", "Compatibility Check", "Validate platform compatibility")
        self.draw_option("P", "Platform Status", "Check installation status")
        self.draw_option("E", "Export Bundle", "Create portable config archive")
        self.draw_option("I", "Import Bundle", "Restore config from archive")

        print()
        self.draw_option("0", "Exit")

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

    def _export_bundle(self) -> None:
        """Interactive export bundle wizard."""
        self.clear_screen()
        self.draw_box("EXPORT BUNDLE")

        c = self.colors

        # Show what will be exported
        self.draw_section("Components to export:")
        print(f"  - {len(self.syncer.agents)} agents")
        print(f"  - {len(self.syncer.skills)} skills")
        print(f"  - {len(self.syncer.commands)} commands")
        print(f"  - {len(self.syncer.hooks)} hooks")
        print(f"  - {len(self.syncer.plugins)} plugins")
        print(f"  - MCP servers config")
        print(f"  - settings.json")
        print(f"  - CLAUDE.md")
        print()

        # Ask about plugins (they can be large)
        include_plugins = self.prompt_confirm("Include plugins? (can be large)")

        # Ask for custom filename
        print()
        custom_path = self.prompt_text("Output filename (leave empty for default)")

        output_path = Path(custom_path) if custom_path else None

        print()
        if self.prompt_confirm("Create export bundle?"):
            try:
                result_path = self.syncer.export_bundle(output_path, include_plugins=include_plugins)
                print()
                self.print_success(f"Bundle created: {result_path}")
            except Exception as e:
                self.print_error(f"Export failed: {e}")

        self.wait_for_key()

    def _import_bundle(self) -> None:
        """Interactive import bundle wizard."""
        self.clear_screen()
        self.draw_box("IMPORT BUNDLE")

        c = self.colors

        # Get bundle path
        bundle_path = self.prompt_text("Path to bundle file (.tar.gz)")
        if not bundle_path:
            self.print_info("Import cancelled")
            self.wait_for_key()
            return

        bundle = Path(bundle_path).expanduser()
        if not bundle.exists():
            self.print_error(f"File not found: {bundle}")
            self.wait_for_key()
            return

        # Show import options
        print()
        self.draw_section("Import options:")
        print("  [1] Replace - Clear existing config and import bundle")
        print("  [2] Merge   - Keep existing, add new from bundle")
        print("  [3] Cancel")
        print()

        choice = self.prompt("Select mode:")

        if choice == '3' or choice.lower() == 'q':
            self.print_info("Import cancelled")
            self.wait_for_key()
            return

        merge = (choice == '2')
        mode_str = "MERGE with" if merge else "REPLACE"

        print()
        self.print_info(f"Mode: {mode_str} existing config")

        # Backup option
        create_backup = self.prompt_confirm("Create backup before import?", default=True)

        print()
        if self.prompt_confirm(f"Proceed with import?"):
            try:
                success = self.syncer.import_bundle(bundle, merge=merge, backup=create_backup)
                print()
                if success:
                    self.print_success("Import complete!")
                    # Reload components
                    self.syncer.load_all_claude()
                else:
                    self.print_error("Import failed")
            except Exception as e:
                self.print_error(f"Import failed: {e}")

        self.wait_for_key()
