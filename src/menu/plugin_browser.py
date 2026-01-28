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

            # Components - now browsable
            self.draw_section("COMPONENTS (select to browse)")
            component_idx = 1
            component_map = {}  # idx -> (type, count)

            if plugin.has_commands:
                cmd_count = self._count_items(plugin.source_path / "commands", "*.md")
                print(f"  {c.colorize(f'[{component_idx}]', c.CYAN, c.BOLD)} Commands: {cmd_count}")
                component_map[component_idx] = ("commands", cmd_count)
                component_idx += 1

            if plugin.has_agents:
                agent_count = self._count_items(plugin.source_path / "agents", "*.md")
                print(f"  {c.colorize(f'[{component_idx}]', c.CYAN, c.BOLD)} Agents: {agent_count}")
                component_map[component_idx] = ("agents", agent_count)
                component_idx += 1

            if plugin.has_skills:
                skills_path = plugin.source_path / "skills"
                skill_count = sum(1 for d in skills_path.iterdir() if d.is_dir()) if skills_path.exists() else 0
                print(f"  {c.colorize(f'[{component_idx}]', c.CYAN, c.BOLD)} Skills: {skill_count}")
                component_map[component_idx] = ("skills", skill_count)
                component_idx += 1

            if plugin.has_hooks:
                print(f"  {c.colorize(f'[{component_idx}]', c.CYAN, c.BOLD)} Hooks: configured")
                component_map[component_idx] = ("hooks", 0)
                component_idx += 1

            if plugin.has_mcp:
                print(f"  {c.colorize(f'[{component_idx}]', c.CYAN, c.BOLD)} MCP Servers: configured")
                component_map[component_idx] = ("mcp", 0)
                component_idx += 1

            if not component_map:
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
            elif choice.isdigit() and int(choice) in component_map:
                comp_type, _ = component_map[int(choice)]
                self._browse_plugin_component(plugin, comp_type)

    def _toggle_exclusion(self, plugin) -> None:
        """Toggle export/sync exclusion for a plugin."""
        is_excluded, message = self.exclusion_manager.toggle_exclusion("plugin", plugin.name)

        if is_excluded:
            self.print_info(f"Plugin '{plugin.name}' is now EXCLUDED from sync/export")
        else:
            self.print_success(f"Plugin '{plugin.name}' is now INCLUDED in sync/export")

    def _browse_plugin_component(self, plugin, comp_type: str) -> None:
        """Browse a specific component type within a plugin."""
        if comp_type == "commands":
            self._browse_plugin_commands(plugin)
        elif comp_type == "agents":
            self._browse_plugin_agents(plugin)
        elif comp_type == "skills":
            self._browse_plugin_skills(plugin)
        elif comp_type == "hooks":
            self._browse_plugin_hooks(plugin)
        elif comp_type == "mcp":
            self._browse_plugin_mcp(plugin)

    def _browse_plugin_commands(self, plugin) -> None:
        """Browse commands within a plugin using arrow-key selection."""
        from menu.base import _get_key

        cmd_dir = plugin.source_path / "commands"
        if not cmd_dir.exists():
            self.print_error("Commands directory not found")
            self.wait_for_key()
            return

        commands = list(cmd_dir.glob("*.md"))
        if not commands:
            self.print_info("No commands found")
            self.wait_for_key()
            return

        selected = 0

        while True:
            self.clear_screen()
            c = self.colors

            self.draw_box(f"COMMANDS: {plugin.name}", f"{len(commands)} commands")

            for idx, cmd_path in enumerate(commands):
                desc = self._parse_frontmatter_field(cmd_path, "description") or "No description"
                desc = format_description(desc, 40)

                if idx == selected:
                    print(c.colorize(f"  > /{cmd_path.stem:<20} {desc}", c.CYAN, c.BOLD))
                else:
                    print(f"    /{cmd_path.stem:<20} {c.colorize(desc, c.DIM)}")

            print()
            print(f"  {c.colorize('[↑/↓] Navigate', c.DIM)}  {c.colorize('[Enter] View', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

            key = _get_key()

            if key == 'up':
                selected = (selected - 1) % len(commands)
            elif key == 'down':
                selected = (selected + 1) % len(commands)
            elif key == 'enter':
                self._show_command_detail(commands[selected], plugin.name)
            elif key == 'quit':
                return

    def _show_command_detail(self, cmd_path: Path, plugin_name: str) -> None:
        """Show detailed view of a command."""
        self.clear_screen()
        c = self.colors

        self.draw_box(f"COMMAND: /{cmd_path.stem}")

        # Parse the file
        content = cmd_path.read_text()
        frontmatter, body = self._split_frontmatter(content)

        # Source info
        self.draw_section("SOURCE")
        print(f"  Plugin: {plugin_name}")
        print(f"  File: {cmd_path}")

        # Description
        desc = frontmatter.get("description", "No description")
        self.draw_section("DESCRIPTION")
        print(f"  {desc}")

        # Allowed tools
        tools = frontmatter.get("allowed-tools", [])
        if tools:
            self.draw_section("ALLOWED TOOLS")
            if isinstance(tools, list):
                print(f"  {', '.join(str(t) for t in tools)}")
            else:
                print(f"  {tools}")

        # Argument hint
        arg_hint = frontmatter.get("argument-hint", "")
        if arg_hint:
            self.draw_section("ARGUMENT HINT")
            print(f"  {arg_hint}")

        # Model
        model = frontmatter.get("model", "")
        if model:
            self.draw_section("MODEL")
            print(f"  {model}")

        # Instructions (body content)
        if body.strip():
            self.draw_section("INSTRUCTIONS")
            lines = body.strip().split('\n')
            for line in lines[:15]:
                # Skip markdown headers that just repeat the name
                if line.startswith('#') and cmd_path.stem in line.lower():
                    continue
                print(f"  {c.colorize(line[:70], c.DIM)}")
            if len(lines) > 15:
                print(f"  {c.colorize(f'... ({len(lines) - 15} more lines)', c.DIM)}")

        print()
        print(f"  {c.colorize('[e] Edit', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

        choice = self.prompt()
        if choice.lower() == 'e':
            import subprocess
            subprocess.run(["code", str(cmd_path)], check=False)
            self.print_success("Opened in editor")
            self.wait_for_key()

    def _browse_plugin_agents(self, plugin) -> None:
        """Browse agents within a plugin using arrow-key selection."""
        from menu.base import _get_key

        agent_dir = plugin.source_path / "agents"
        if not agent_dir.exists():
            self.print_error("Agents directory not found")
            self.wait_for_key()
            return

        agents = list(agent_dir.glob("*.md"))
        if not agents:
            self.print_info("No agents found")
            self.wait_for_key()
            return

        selected = 0

        while True:
            self.clear_screen()
            c = self.colors

            self.draw_box(f"AGENTS: {plugin.name}", f"{len(agents)} agents")

            for idx, agent_path in enumerate(agents):
                desc = self._parse_frontmatter_field(agent_path, "description") or "No description"
                desc = format_description(desc, 40)

                if idx == selected:
                    print(c.colorize(f"  > {agent_path.stem:<22} {desc}", c.CYAN, c.BOLD))
                else:
                    print(f"    {agent_path.stem:<22} {c.colorize(desc, c.DIM)}")

            print()
            print(f"  {c.colorize('[↑/↓] Navigate', c.DIM)}  {c.colorize('[Enter] View', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

            key = _get_key()

            if key == 'up':
                selected = (selected - 1) % len(agents)
            elif key == 'down':
                selected = (selected + 1) % len(agents)
            elif key == 'enter':
                self._show_agent_detail(agents[selected], plugin.name)
            elif key == 'quit':
                return

    def _show_agent_detail(self, agent_path: Path, plugin_name: str) -> None:
        """Show detailed view of an agent."""
        self.clear_screen()
        c = self.colors

        self.draw_box(f"AGENT: {agent_path.stem}")

        # Parse the file
        content = agent_path.read_text()
        frontmatter, body = self._split_frontmatter(content)

        # Source info
        self.draw_section("SOURCE")
        print(f"  Plugin: {plugin_name}")
        print(f"  File: {agent_path}")

        # Description
        desc = frontmatter.get("description", "No description")
        self.draw_section("DESCRIPTION")
        # Word wrap long descriptions
        words = desc.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > 65:
                lines.append(current_line)
                current_line = word
            else:
                current_line = f"{current_line} {word}" if current_line else word
        if current_line:
            lines.append(current_line)
        for line in lines:
            print(f"  {line}")

        # Tools
        tools = frontmatter.get("tools", [])
        if tools:
            self.draw_section("TOOLS")
            if isinstance(tools, list):
                print(f"  {', '.join(str(t) for t in tools)}")
            else:
                print(f"  {tools}")

        # Model
        model = frontmatter.get("model", "")
        if model:
            self.draw_section("MODEL")
            print(f"  {model}")

        # Color
        color = frontmatter.get("color", "")
        if color:
            self.draw_section("COLOR")
            print(f"  {color}")

        # When to use (from description or body)
        when_to_use = frontmatter.get("when-to-use", "")
        if when_to_use:
            self.draw_section("WHEN TO USE")
            print(f"  {when_to_use}")

        # Agent content/instructions (body)
        if body.strip():
            self.draw_section("AGENT PROMPT")
            lines = body.strip().split('\n')
            for line in lines[:20]:
                print(f"  {c.colorize(line[:70], c.DIM)}")
            if len(lines) > 20:
                print(f"  {c.colorize(f'... ({len(lines) - 20} more lines)', c.DIM)}")

        print()
        print(f"  {c.colorize('[e] Edit', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

        choice = self.prompt()
        if choice.lower() == 'e':
            import subprocess
            subprocess.run(["code", str(agent_path)], check=False)
            self.print_success("Opened in editor")
            self.wait_for_key()

    def _browse_plugin_skills(self, plugin) -> None:
        """Browse skills within a plugin using arrow-key selection."""
        from menu.base import _get_key

        skills_dir = plugin.source_path / "skills"
        if not skills_dir.exists():
            self.print_error("Skills directory not found")
            self.wait_for_key()
            return

        skills = [d for d in skills_dir.iterdir() if d.is_dir()]
        if not skills:
            self.print_info("No skills found")
            self.wait_for_key()
            return

        selected = 0

        while True:
            self.clear_screen()
            c = self.colors

            self.draw_box(f"SKILLS: {plugin.name}", f"{len(skills)} skills")

            for idx, skill_path in enumerate(skills):
                skill_md = skill_path / "SKILL.md"
                desc = "No description"
                if skill_md.exists():
                    desc = self._parse_frontmatter_field(skill_md, "description") or "No description"
                desc = format_description(desc, 40)

                if idx == selected:
                    print(c.colorize(f"  > {skill_path.name:<22} {desc}", c.CYAN, c.BOLD))
                else:
                    print(f"    {skill_path.name:<22} {c.colorize(desc, c.DIM)}")

            print()
            print(f"  {c.colorize('[↑/↓] Navigate', c.DIM)}  {c.colorize('[Enter] View', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

            key = _get_key()

            if key == 'up':
                selected = (selected - 1) % len(skills)
            elif key == 'down':
                selected = (selected + 1) % len(skills)
            elif key == 'enter':
                self._show_skill_detail(skills[selected], plugin.name)
            elif key == 'quit':
                return

    def _show_skill_detail(self, skill_path: Path, plugin_name: str) -> None:
        """Show detailed view of a skill."""
        self.clear_screen()
        c = self.colors
        b = self.box

        self.draw_box(f"SKILL: {skill_path.name}")

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            print(f"  {c.colorize('No SKILL.md found', c.RED)}")
            self.wait_for_key()
            return

        # Parse the file
        content = skill_md.read_text()
        frontmatter, body = self._split_frontmatter(content)

        # Source info
        self.draw_section("SOURCE")
        print(f"  Plugin: {plugin_name}")
        print(f"  Path: {skill_path}")

        # Description
        desc = frontmatter.get("description", "No description")
        self.draw_section("DESCRIPTION")
        words = desc.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > 65:
                lines.append(current_line)
                current_line = word
            else:
                current_line = f"{current_line} {word}" if current_line else word
        if current_line:
            lines.append(current_line)
        for line in lines:
            print(f"  {line}")

        # Structure
        self.draw_section("STRUCTURE")
        print(f"  {skill_path.name}/")
        for item in sorted(skill_path.iterdir()):
            if item.is_file():
                print(f"    {c.colorize(b['check'], c.GREEN)} {item.name}")
            elif item.is_dir():
                file_count = sum(1 for f in item.rglob("*") if f.is_file())
                print(f"    {c.colorize(b['check'], c.GREEN)} {item.name}/ ({file_count} files)")

        # Skill content (body)
        if body.strip():
            self.draw_section("SKILL CONTENT")
            lines = body.strip().split('\n')
            for line in lines[:20]:
                print(f"  {c.colorize(line[:70], c.DIM)}")
            if len(lines) > 20:
                print(f"  {c.colorize(f'... ({len(lines) - 20} more lines)', c.DIM)}")

        print()
        print(f"  {c.colorize('[e] Edit SKILL.md', c.DIM)}  {c.colorize('[o] Open folder', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

        choice = self.prompt()
        if choice.lower() == 'e':
            import subprocess
            subprocess.run(["code", str(skill_md)], check=False)
            self.print_success("Opened in editor")
            self.wait_for_key()
        elif choice.lower() == 'o':
            import subprocess
            subprocess.run(["code", str(skill_path)], check=False)
            self.print_success("Opened folder in editor")
            self.wait_for_key()

    def _browse_plugin_hooks(self, plugin) -> None:
        """Browse hooks within a plugin."""
        import json

        self.clear_screen()
        c = self.colors

        self.draw_box(f"HOOKS: {plugin.name}")

        # Check for hooks in plugin.json
        plugin_json = plugin.source_path / ".claude-plugin" / "plugin.json"
        hooks_found = False

        if plugin_json.exists():
            try:
                manifest = json.loads(plugin_json.read_text())
                hooks = manifest.get("hooks", {})

                if hooks:
                    hooks_found = True
                    for event, event_hooks in hooks.items():
                        self.draw_section(f"{event}:")
                        if isinstance(event_hooks, list):
                            for hook_config in event_hooks:
                                matcher = hook_config.get("matcher", "*")
                                hook_list = hook_config.get("hooks", [])
                                for h in hook_list:
                                    hook_type = h.get("type", "command")
                                    cmd = h.get("command", h.get("prompt", ""))
                                    timeout = h.get("timeout", 60)
                                    print(f"  Matcher: {matcher}")
                                    print(f"    Type: {hook_type}")
                                    print(f"    {c.colorize(cmd[:60], c.DIM)}")
                                    print(f"    Timeout: {timeout}s")
                                    print()
            except Exception as e:
                print(f"  {c.colorize(f'Error parsing hooks: {e}', c.RED)}")

        # Also check hooks/ directory
        hooks_dir = plugin.source_path / "hooks"
        if hooks_dir.exists():
            hook_files = list(hooks_dir.glob("*.json")) + list(hooks_dir.glob("*.md"))
            if hook_files:
                hooks_found = True
                self.draw_section("Hook Files:")
                for hf in hook_files:
                    print(f"  {c.colorize(b['check'], c.GREEN)} {hf.name}")

        if not hooks_found:
            print(f"  {c.colorize('No hooks configuration found', c.DIM)}")

        print()
        print(f"  {c.colorize('[q] Back', c.DIM)}")
        self.wait_for_key()

    def _browse_plugin_mcp(self, plugin) -> None:
        """Browse MCP servers within a plugin."""
        import json

        self.clear_screen()
        c = self.colors

        self.draw_box(f"MCP SERVERS: {plugin.name}")

        # Check for MCP in plugin.json
        plugin_json = plugin.source_path / ".claude-plugin" / "plugin.json"
        mcp_found = False

        if plugin_json.exists():
            try:
                manifest = json.loads(plugin_json.read_text())
                mcp_servers = manifest.get("mcpServers", {})

                if mcp_servers:
                    mcp_found = True
                    for server_name, server_config in mcp_servers.items():
                        self.draw_section(f"{server_name}:")
                        print(f"  Command: {server_config.get('command', 'N/A')}")
                        args = server_config.get('args', [])
                        if args:
                            print(f"  Args: {' '.join(args)}")
                        env = server_config.get('env', {})
                        if env:
                            print(f"  Environment:")
                            for k, v in env.items():
                                print(f"    {k}={v[:30]}{'...' if len(str(v)) > 30 else ''}")
                        print()
            except Exception as e:
                print(f"  {c.colorize(f'Error parsing MCP config: {e}', c.RED)}")

        # Also check .mcp.json
        mcp_json = plugin.source_path / ".mcp.json"
        if mcp_json.exists():
            try:
                mcp_config = json.loads(mcp_json.read_text())
                mcp_found = True
                self.draw_section("From .mcp.json:")
                for server_name, server_config in mcp_config.get("mcpServers", {}).items():
                    print(f"  {server_name}: {server_config.get('command', 'N/A')}")
            except Exception:
                pass

        if not mcp_found:
            print(f"  {c.colorize('No MCP servers configured', c.DIM)}")

        print()
        print(f"  {c.colorize('[q] Back', c.DIM)}")
        self.wait_for_key()

    def _parse_frontmatter_field(self, file_path: Path, field: str) -> str:
        """Parse a single field from YAML frontmatter."""
        try:
            content = file_path.read_text()
            if not content.startswith("---"):
                return ""

            end_idx = content.find("---", 3)
            if end_idx == -1:
                return ""

            frontmatter = content[3:end_idx]
            for line in frontmatter.split('\n'):
                if line.startswith(f"{field}:"):
                    value = line[len(field) + 1:].strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    return value
            return ""
        except Exception:
            return ""

    def _split_frontmatter(self, content: str) -> tuple[dict, str]:
        """Split content into frontmatter dict and body."""
        frontmatter = {}
        body = content

        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx != -1:
                fm_text = content[3:end_idx]
                body = content[end_idx + 3:].strip()

                # Simple YAML parsing
                current_key = None
                current_value = []

                for line in fm_text.split('\n'):
                    line = line.rstrip()
                    if not line:
                        continue

                    # Check if this is a new key
                    if ':' in line and not line.startswith(' ') and not line.startswith('-'):
                        # Save previous key if exists
                        if current_key:
                            if len(current_value) == 1:
                                frontmatter[current_key] = current_value[0]
                            elif current_value:
                                frontmatter[current_key] = current_value

                        parts = line.split(':', 1)
                        current_key = parts[0].strip()
                        value = parts[1].strip() if len(parts) > 1 else ""

                        # Handle inline value
                        if value:
                            # Remove quotes
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            # Handle inline list
                            elif value.startswith('[') and value.endswith(']'):
                                items = value[1:-1].split(',')
                                value = [i.strip().strip('"\'') for i in items if i.strip()]
                            current_value = [value] if not isinstance(value, list) else value
                        else:
                            current_value = []
                    elif line.startswith('  -') or line.startswith('- '):
                        # List item
                        item = line.lstrip(' -').strip()
                        if item.startswith('"') and item.endswith('"'):
                            item = item[1:-1]
                        current_value.append(item)

                # Save last key
                if current_key:
                    if len(current_value) == 1:
                        frontmatter[current_key] = current_value[0]
                    elif current_value:
                        frontmatter[current_key] = current_value

        return frontmatter, body

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
