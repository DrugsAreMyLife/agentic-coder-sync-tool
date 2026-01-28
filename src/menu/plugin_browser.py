"""Plugin Browser for exploring and managing plugins."""

from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.formatters import format_description
from utils.exclusion_manager import ExclusionManager


class PluginBrowser(BaseMenu):
    """Interactive plugin browser."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.plugins = syncer.plugins
        self.exclusion_manager = ExclusionManager()

    def run(self) -> Optional[str]:
        """Run the plugin browser loop."""
        while True:
            self.clear_screen()
            self._draw_list()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice.lower() == 's':
                self._do_search()
            elif choice.lower() == 'n':
                self._create_plugin()
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(self.plugins):
                    sorted_plugins = self._get_sorted_plugins()
                    self._show_plugin_detail(sorted_plugins[idx - 1])

    def _get_sorted_plugins(self) -> list:
        """Get plugins sorted by source (official, marketplace, local)."""
        official = []
        marketplace = []
        local = []

        for plugin in self.plugins:
            path_str = str(plugin.source_path)
            if "claude-plugins-official" in path_str:
                official.append(plugin)
            elif "cc-marketplace" in path_str:
                marketplace.append(plugin)
            else:
                local.append(plugin)

        return official + marketplace + local

    def _draw_list(self) -> None:
        """Draw the plugin list."""
        c = self.colors
        b = self.box
        total = len(self.plugins)

        self.draw_box("PLUGIN BROWSER", f"{total} plugins loaded")

        sorted_plugins = self._get_sorted_plugins()

        # Group by source
        official = [p for p in sorted_plugins if "claude-plugins-official" in str(p.source_path)]
        marketplace = [p for p in sorted_plugins if "cc-marketplace" in str(p.source_path)]
        local = [p for p in sorted_plugins if p not in official and p not in marketplace]

        idx = 1

        if official:
            self.draw_section("Official (claude-plugins-official):")
            for plugin in official[:5]:
                features = self._get_feature_flags(plugin)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {plugin.name:<25} {c.colorize(features, c.DIM)}")
                idx += 1
            if len(official) > 5:
                print(f"      {c.colorize(f'... and {len(official) - 5} more', c.DIM)}")

        if marketplace:
            self.draw_section("Marketplace (cc-marketplace):")
            for plugin in marketplace[:5]:
                features = self._get_feature_flags(plugin)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {plugin.name:<25} {c.colorize(features, c.DIM)}")
                idx += 1
            if len(marketplace) > 5:
                print(f"      {c.colorize(f'... and {len(marketplace) - 5} more', c.DIM)}")

        if local:
            self.draw_section("Local (~/.claude/plugins):")
            for plugin in local[:5]:
                features = self._get_feature_flags(plugin)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {plugin.name:<25} {c.colorize(features, c.DIM)}")
                idx += 1
            if len(local) > 5:
                print(f"      {c.colorize(f'... and {len(local) - 5} more', c.DIM)}")

        print()
        print(f"  {c.colorize('[s] Search', c.DIM)}  {c.colorize('[n] New plugin', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _get_feature_flags(self, plugin) -> str:
        """Get feature flags string for a plugin."""
        flags = []
        if plugin.has_commands:
            flags.append("cmds")
        if plugin.has_agents:
            flags.append("agents")
        if plugin.has_skills:
            flags.append("skills")
        if plugin.has_hooks:
            flags.append("hooks")
        if plugin.has_mcp:
            flags.append("mcp")
        return f"[{', '.join(flags)}]" if flags else ""

    def _do_search(self) -> None:
        """Search plugins."""
        query = self.prompt_text("Search plugins")
        if not query:
            return

        matching = [p for p in self.plugins if query.lower() in p.name.lower()
                    or query.lower() in (p.description or "").lower()]

        self.clear_screen()
        self.draw_box("SEARCH RESULTS", f"'{query}'")

        c = self.colors
        if not matching:
            print(f"  {c.colorize('No plugins found.', c.DIM)}")
        else:
            for idx, plugin in enumerate(matching[:10], 1):
                features = self._get_feature_flags(plugin)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {plugin.name:<25} {c.colorize(features, c.DIM)}")

        self.wait_for_key()

    def _show_plugin_detail(self, plugin) -> None:
        """Show detailed view of a plugin."""
        while True:
            self.clear_screen()
            c = self.colors
            b = self.box

            self.draw_box(f"PLUGIN: {plugin.name}")

            # Info
            self.draw_section("INFO")
            print(f"  Version: {plugin.version}")
            print(f"  Author: {plugin.author or 'Unknown'}")
            print(f"  Path: {plugin.source_path}")

            # Description
            if plugin.description:
                self.draw_section("DESCRIPTION")
                desc = format_description(plugin.description, 200)
                print(f"  {desc}")

            # Components
            self.draw_section("COMPONENTS")
            components = []
            if plugin.has_commands:
                cmd_count = self._count_items(plugin.source_path / "commands", "*.md")
                components.append(f"Commands: {cmd_count}")
            if plugin.has_agents:
                agent_count = self._count_items(plugin.source_path / "agents", "*.md")
                components.append(f"Agents: {agent_count}")
            if plugin.has_skills:
                skill_count = sum(1 for d in (plugin.source_path / "skills").iterdir() if d.is_dir())
                components.append(f"Skills: {skill_count}")
            if plugin.has_hooks:
                components.append("Hooks: configured")
            if plugin.has_mcp:
                components.append("MCP: configured")

            for comp in components:
                print(f"  {c.colorize(b['check'], c.GREEN)} {comp}")

            if not components:
                print(f"  {c.colorize('No components', c.DIM)}")

            # Export/Sync Exclusion Status
            self.draw_section("EXPORT STATUS")
            exclusion_status = self.exclusion_manager.get_exclusion_status("plugin", plugin.name)
            if exclusion_status["is_excluded"]:
                rule = exclusion_status["matched_rule"]
                if exclusion_status["is_explicit"]:
                    print(f"  {c.colorize('[EXCLUDED]', c.RED, c.BOLD)} Manually excluded from sync/export")
                else:
                    print(f"  {c.colorize('[EXCLUDED]', c.YELLOW)} Matches pattern: {rule.pattern}")
                    print(f"  {c.colorize(f'Reason: {rule.reason}', c.DIM)}")
            else:
                print(f"  {c.colorize('[INCLUDED]', c.GREEN)} Will be included in sync/export")

            print()
            print(f"  {c.colorize('[o] Open in editor', c.DIM)}  {c.colorize('[x] Toggle Exclusion', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

            choice = self.prompt()

            if choice.lower() == 'q':
                return
            elif choice.lower() == 'o':
                import subprocess
                subprocess.run(["code", str(plugin.source_path)], check=False)
                self.print_success("Opened in editor")
                self.wait_for_key()
            elif choice.lower() == 'x':
                self._toggle_exclusion(plugin)

    def _toggle_exclusion(self, plugin) -> None:
        """Toggle export/sync exclusion for a plugin."""
        is_excluded, message = self.exclusion_manager.toggle_exclusion("plugin", plugin.name)

        if is_excluded:
            self.print_info(f"Plugin '{plugin.name}' is now EXCLUDED from sync/export")
        else:
            self.print_success(f"Plugin '{plugin.name}' is now INCLUDED in sync/export")

    def _count_items(self, path: Path, pattern: str) -> int:
        """Count items matching pattern in a directory."""
        if not path.exists():
            return 0
        return len(list(path.glob(pattern)))

    def _create_plugin(self) -> None:
        """Create a new plugin interactively."""
        c = self.colors
        self.clear_screen()

        self.draw_box("NEW PLUGIN WIZARD", "1/3")

        name = self.prompt_text("Plugin name (lowercase, hyphens)")
        if not name:
            return

        description = self.prompt_text("Description")
        author = self.prompt_text("Author name")

        self.clear_screen()
        self.draw_box("NEW PLUGIN WIZARD", "2/3")

        print("  Include components?")
        print("  [1] commands/    - Slash commands")
        print("  [2] agents/      - Custom agents")
        print("  [3] skills/      - Skills")
        print("  [4] hooks/       - Event hooks")
        print()
        print("  Select (comma-separated, or none):")

        comp_choice = self.prompt()
        include_commands = "1" in comp_choice
        include_agents = "2" in comp_choice
        include_skills = "3" in comp_choice
        include_hooks = "4" in comp_choice

        # Create plugin directory
        plugins_dir = self.syncer.claude_plugins
        plugins_dir.mkdir(parents=True, exist_ok=True)

        plugin_path = plugins_dir / name
        if plugin_path.exists():
            self.print_error(f"Plugin '{name}' already exists")
            self.wait_for_key()
            return

        plugin_path.mkdir(parents=True)

        # Create .claude-plugin directory and plugin.json
        claude_plugin_dir = plugin_path / ".claude-plugin"
        claude_plugin_dir.mkdir()

        import json
        manifest = {
            "name": name,
            "version": "1.0.0",
            "description": description,
            "author": {"name": author} if author else {},
        }
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2))

        # Create component directories
        if include_commands:
            (plugin_path / "commands").mkdir()
        if include_agents:
            (plugin_path / "agents").mkdir()
        if include_skills:
            (plugin_path / "skills").mkdir()
        if include_hooks:
            (plugin_path / "hooks").mkdir()

        self.clear_screen()
        self.draw_box("NEW PLUGIN WIZARD", "3/3")

        self.print_success(f"Created plugin at {plugin_path}")

        # Reload plugins
        self.syncer.plugins = self.syncer.load_claude_plugins()
        self.plugins = self.syncer.plugins

        self.wait_for_key()
