"""Hook Browser for viewing and managing event hooks."""

import json
from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.formatters import truncate
from utils.exclusion_manager import ExclusionManager


class HookBrowser(BaseMenu):
    """Interactive hook browser with enable/disable functionality."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.hooks = syncer.hooks
        self.exclusion_manager = ExclusionManager()

    def run(self) -> Optional[str]:
        """Run the hook browser loop."""
        while True:
            self.clear_screen()
            self._draw_list()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice.lower() == 'n':
                self._create_hook()
            elif choice.lower() == 'e':
                self._edit_settings()
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(self.hooks):
                    self._show_hook_detail(self.hooks[idx - 1])

    def _draw_list(self) -> None:
        """Draw the hook list grouped by event."""
        c = self.colors

        total = len(self.hooks)
        self.draw_box("HOOK BROWSER", f"{total} hooks active")

        # Group by event
        by_event = {}
        for hook in self.hooks:
            by_event.setdefault(hook.event, []).append(hook)

        idx = 1
        for event, hooks in sorted(by_event.items()):
            self.draw_section(f"{event}:")

            for hook in hooks[:5]:
                matcher = hook.matcher if len(hook.matcher) < 20 else hook.matcher[:17] + "..."
                cmd_preview = truncate(hook.command, 30)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} [{matcher}] {c.colorize(cmd_preview, c.DIM)}")
                idx += 1

            if len(hooks) > 5:
                print(f"      {c.colorize(f'... and {len(hooks) - 5} more', c.DIM)}")

        if not self.hooks:
            print(f"  {c.colorize('No hooks configured', c.DIM)}")

        print()
        print(f"  {c.colorize('[n] New hook', c.DIM)}  {c.colorize('[e] Edit settings.json', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _show_hook_detail(self, hook) -> None:
        """Show detailed view of a hook."""
        c = self.colors

        self.clear_screen()
        self.draw_box(f"HOOK: {hook.event}")

        self.draw_section("EVENT")
        print(f"  {hook.event}")

        self.draw_section("MATCHER")
        print(f"  {hook.matcher}")

        self.draw_section("TYPE")
        print(f"  {hook.hook_type}")

        self.draw_section("COMMAND/PROMPT")
        # Word wrap the command
        command = hook.command
        words = command.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > 50:
                lines.append(current_line)
                current_line = word
            else:
                current_line = f"{current_line} {word}" if current_line else word
        if current_line:
            lines.append(current_line)

        for line in lines[:5]:
            print(f"  {line}")
        if len(lines) > 5:
            print(f"  {c.colorize('...', c.DIM)}")

        self.draw_section("TIMEOUT")
        print(f"  {hook.timeout} seconds")

        if hook.source_path:
            self.draw_section("SOURCE")
            print(f"  {hook.source_path}")

        # Export/Sync Exclusion Status
        # Use a unique identifier for hooks (event:matcher)
        hook_id = f"{hook.event}:{hook.matcher}"
        self.draw_section("EXPORT STATUS")
        exclusion_status = self.exclusion_manager.get_exclusion_status("hook", hook_id)
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
        print(f"  {c.colorize('[d] Disable', c.DIM)}  {c.colorize('[x] Toggle Exclusion', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

        choice = self.prompt()
        if choice.lower() == 'd':
            self._disable_hook(hook)
        elif choice.lower() == 'x':
            self._toggle_exclusion(hook)

    def _toggle_exclusion(self, hook) -> None:
        """Toggle export/sync exclusion for a hook."""
        # Use a unique identifier for hooks (event:matcher)
        hook_id = f"{hook.event}:{hook.matcher}"
        is_excluded, message = self.exclusion_manager.toggle_exclusion("hook", hook_id)

        if is_excluded:
            self.print_info(f"Hook '{hook.event}:{hook.matcher}' is now EXCLUDED from sync/export")
        else:
            self.print_success(f"Hook '{hook.event}:{hook.matcher}' is now INCLUDED in sync/export")

    def _disable_hook(self, hook) -> None:
        """Disable a hook (remove from settings)."""
        if not self.prompt_confirm("Disable this hook?", default=False):
            return

        settings_path = self.syncer.claude_settings
        if not settings_path.exists():
            self.print_error("Settings file not found")
            self.wait_for_key()
            return

        try:
            settings = json.loads(settings_path.read_text())
            hooks_config = settings.get("hooks", {})

            if hook.event in hooks_config:
                # Find and remove the matching hook
                for matcher_config in hooks_config[hook.event]:
                    if matcher_config.get("matcher") == hook.matcher:
                        hook_list = matcher_config.get("hooks", [])
                        for i, h in enumerate(hook_list):
                            if h.get("command") == hook.command or h.get("prompt") == hook.command:
                                hook_list.pop(i)
                                break

                # Clean up empty entries
                hooks_config[hook.event] = [m for m in hooks_config[hook.event] if m.get("hooks")]
                if not hooks_config[hook.event]:
                    del hooks_config[hook.event]

                settings["hooks"] = hooks_config
                settings_path.write_text(json.dumps(settings, indent=2))

                self.print_success("Hook disabled")

                # Reload hooks
                self.syncer.hooks = self.syncer.load_claude_hooks()
                self.hooks = self.syncer.hooks
            else:
                self.print_error("Hook not found in settings")

        except Exception as e:
            self.print_error(f"Error: {e}")

        self.wait_for_key()

    def _edit_settings(self) -> None:
        """Open settings.json in editor."""
        import subprocess

        settings_path = self.syncer.claude_settings
        if not settings_path.exists():
            # Create default settings
            settings_path.write_text(json.dumps({"hooks": {}}, indent=2))

        subprocess.run(["code", str(settings_path)], check=False)
        self.print_success("Opened settings.json in editor")
        self.wait_for_key()

    def _create_hook(self) -> None:
        """Create a new hook interactively."""
        c = self.colors
        self.clear_screen()

        self.draw_box("NEW HOOK WIZARD", "1/4")

        print("  Select event type:")
        print("  [1] PreToolUse     - Before tool execution")
        print("  [2] PostToolUse    - After tool execution")
        print("  [3] SessionStart   - When session begins")
        print("  [4] Stop           - When agent stops")

        event_choice = self.prompt()
        event_map = {
            "1": "PreToolUse",
            "2": "PostToolUse",
            "3": "SessionStart",
            "4": "Stop",
        }
        event = event_map.get(event_choice, "PreToolUse")

        self.clear_screen()
        self.draw_box("NEW HOOK WIZARD", "2/4")

        print(f"  Event: {event}")
        print()

        if event in ("PreToolUse", "PostToolUse"):
            matcher = self.prompt_text("Tool matcher (regex, e.g., 'Write|Edit' or '*')")
        else:
            matcher = "*"

        self.clear_screen()
        self.draw_box("NEW HOOK WIZARD", "3/4")

        print("  Select hook type:")
        print("  [1] command  - Shell command to execute")
        print("  [2] prompt   - AI prompt for validation")

        type_choice = self.prompt()
        hook_type = "prompt" if type_choice == "2" else "command"

        if hook_type == "command":
            command = self.prompt_text("Shell command")
        else:
            command = self.prompt_text("Validation prompt")

        timeout = self.prompt_text("Timeout in seconds", "60")
        try:
            timeout = int(timeout)
        except:
            timeout = 60

        # Add to settings
        settings_path = self.syncer.claude_settings
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
        else:
            settings = {}

        if "hooks" not in settings:
            settings["hooks"] = {}

        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        # Find or create matcher entry
        matcher_found = False
        for matcher_config in settings["hooks"][event]:
            if matcher_config.get("matcher") == matcher:
                matcher_config["hooks"].append({
                    "type": hook_type,
                    "command" if hook_type == "command" else "prompt": command,
                    "timeout": timeout,
                })
                matcher_found = True
                break

        if not matcher_found:
            settings["hooks"][event].append({
                "matcher": matcher,
                "hooks": [{
                    "type": hook_type,
                    "command" if hook_type == "command" else "prompt": command,
                    "timeout": timeout,
                }]
            })

        settings_path.write_text(json.dumps(settings, indent=2))

        self.clear_screen()
        self.draw_box("NEW HOOK WIZARD", "4/4")

        self.print_success(f"Created {event} hook for '{matcher}'")

        # Reload hooks
        self.syncer.hooks = self.syncer.load_claude_hooks()
        self.hooks = self.syncer.hooks

        self.wait_for_key()
