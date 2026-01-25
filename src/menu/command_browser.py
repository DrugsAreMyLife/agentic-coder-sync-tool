"""Command Browser for viewing and creating slash commands."""

from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.formatters import format_description, format_tools_list


class CommandBrowser(BaseMenu):
    """Interactive command browser."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.commands = syncer.commands
        self._load_plugin_commands()

    def _load_plugin_commands(self) -> None:
        """Load commands from plugins."""
        self.plugin_commands = []

        for plugin in self.syncer.plugins:
            cmd_dir = plugin.source_path / "commands"
            if cmd_dir.exists():
                for cmd_file in cmd_dir.glob("*.md"):
                    self.plugin_commands.append({
                        "name": cmd_file.stem,
                        "plugin": plugin.name,
                        "path": cmd_file,
                    })

    def run(self) -> Optional[str]:
        """Run the command browser loop."""
        while True:
            self.clear_screen()
            self._draw_list()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice.lower() == 'n':
                self._create_command()
            elif choice.isdigit():
                idx = int(choice)
                self._show_command_detail(idx)

    def _draw_list(self) -> None:
        """Draw the command list."""
        c = self.colors

        total = len(self.commands) + len(self.plugin_commands)
        self.draw_box("COMMAND BROWSER", f"{total} commands")

        idx = 1

        # Plugin commands
        if self.plugin_commands:
            self.draw_section("From Plugins:")
            for cmd in self.plugin_commands[:10]:
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} /{cmd['name']:<20} {c.colorize(cmd['plugin'], c.DIM)}")
                idx += 1
            if len(self.plugin_commands) > 10:
                print(f"      {c.colorize(f'... and {len(self.plugin_commands) - 10} more', c.DIM)}")

        # User commands
        if self.commands:
            self.draw_section("User Commands:")
            for cmd in self.commands[:10]:
                desc = format_description(cmd.description, 30)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} /{cmd.name:<20} {c.colorize(desc, c.DIM)}")
                idx += 1
        else:
            self.draw_section("User Commands:")
            print(f"  {c.colorize('(none configured)', c.DIM)}")

        print()
        print(f"  {c.colorize('[n] New command', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _show_command_detail(self, idx: int) -> None:
        """Show command detail."""
        c = self.colors
        b = self.box

        # Determine which command
        total_plugin = len(self.plugin_commands)

        if idx <= total_plugin:
            cmd = self.plugin_commands[idx - 1]
            self.clear_screen()
            self.draw_box(f"COMMAND: /{cmd['name']}")

            self.draw_section("SOURCE")
            print(f"  Plugin: {cmd['plugin']}")
            print(f"  Path: {cmd['path']}")

            # Read content
            if cmd['path'].exists():
                content = cmd['path'].read_text()
                self.draw_section("CONTENT PREVIEW")
                lines = content.split('\n')[:10]
                for line in lines:
                    print(f"  {c.colorize(line[:60], c.DIM)}")
                if len(content.split('\n')) > 10:
                    print(f"  {c.colorize('...', c.DIM)}")

        elif idx <= total_plugin + len(self.commands):
            cmd = self.commands[idx - total_plugin - 1]
            self.clear_screen()
            self.draw_box(f"COMMAND: /{cmd.name}")

            self.draw_section("DESCRIPTION")
            print(f"  {format_description(cmd.description, 200)}")

            if cmd.allowed_tools:
                self.draw_section("ALLOWED TOOLS")
                print(f"  {format_tools_list(cmd.allowed_tools)}")

            if cmd.argument_hint:
                self.draw_section("ARGUMENT HINT")
                print(f"  {cmd.argument_hint}")

            self.draw_section("PATH")
            print(f"  {cmd.source_path}")
        else:
            self.print_error("Invalid selection")
            self.wait_for_key()
            return

        print()
        print(f"  {c.colorize('[e] Edit', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

        choice = self.prompt()
        if choice.lower() == 'e':
            import subprocess
            if idx <= total_plugin:
                subprocess.run(["code", str(self.plugin_commands[idx - 1]['path'])], check=False)
            else:
                subprocess.run(["code", str(self.commands[idx - total_plugin - 1].source_path)], check=False)
            self.print_success("Opened in editor")
            self.wait_for_key()

    def _create_command(self) -> None:
        """Create a new command interactively."""
        c = self.colors
        self.clear_screen()

        self.draw_box("NEW COMMAND WIZARD", "1/3")

        name = self.prompt_text("Command name (without /)")
        if not name:
            return

        description = self.prompt_text("Description")
        argument_hint = self.prompt_text("Argument hint (optional)")

        self.clear_screen()
        self.draw_box("NEW COMMAND WIZARD", "2/3")

        print("  Select allowed tools:")
        print("  [1] All tools (*)")
        print("  [2] Read-only (Read, Grep, Glob)")
        print("  [3] Read/Write (Read, Write, Edit, Grep, Glob)")
        print("  [4] Custom selection")

        tool_choice = self.prompt()
        if tool_choice == "1":
            tools = ["*"]
        elif tool_choice == "2":
            tools = ["Read", "Grep", "Glob"]
        elif tool_choice == "3":
            tools = ["Read", "Write", "Edit", "Grep", "Glob"]
        elif tool_choice == "4":
            tools_input = self.prompt_text("Tools (comma-separated)")
            tools = [t.strip() for t in tools_input.split(",")]
        else:
            tools = ["*"]

        # Create command file
        commands_dir = self.syncer.claude_commands
        commands_dir.mkdir(parents=True, exist_ok=True)

        cmd_path = commands_dir / f"{name}.md"
        if cmd_path.exists():
            self.print_error(f"Command '/{name}' already exists")
            self.wait_for_key()
            return

        tools_str = ", ".join(tools)
        content = f"""---
description: "{description}"
allowed-tools: [{tools_str}]
"""
        if argument_hint:
            content += f'argument-hint: "{argument_hint}"\n'

        content += f"""---

# /{name}

{description}

## Instructions

[Add command instructions here]
"""

        cmd_path.write_text(content)

        self.clear_screen()
        self.draw_box("NEW COMMAND WIZARD", "3/3")

        self.print_success(f"Created {cmd_path}")

        # Reload commands
        self.syncer.commands = self.syncer.load_claude_commands()
        self.commands = self.syncer.commands

        self.wait_for_key()
