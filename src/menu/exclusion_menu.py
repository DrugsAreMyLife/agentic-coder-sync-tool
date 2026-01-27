"""Exclusion Menu for managing private/excluded components."""

import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.exclusion_manager import ExclusionManager


class ExclusionMenu(BaseMenu):
    """Interactive menu for managing component exclusions."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.manager = ExclusionManager()

    def run(self) -> Optional[str]:
        """Run the exclusion menu loop."""
        while True:
            self.clear_screen()
            self._draw_menu()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice == '1':
                self._list_rules()
            elif choice == '2':
                self._add_rule()
            elif choice == '3':
                self._remove_rule()
            elif choice == '4':
                self._preview_exclusions()
            elif choice == '5':
                self._import_export()

    def _draw_menu(self) -> None:
        """Draw the exclusion menu."""
        c = self.colors

        self.draw_box("EXCLUSION MANAGER")

        # Show summary
        summary = self.manager.get_summary()
        print(f"  Total rules: {summary['total_rules']}")
        print(f"  Sync-only: {summary['sync_only']} | Export-only: {summary['export_only']} | Both: {summary['both']}")
        print()

        # Menu options
        self.draw_option("1", "List Rules", "View all exclusion rules")
        print()
        self.draw_option("2", "Add Rule", "Create new exclusion rule")
        print()
        self.draw_option("3", "Remove Rule", "Delete an exclusion rule")
        print()
        self.draw_option("4", "Preview", "See what would be excluded")
        print()
        self.draw_option("5", "Import/Export", "Share exclusion rules")
        print()
        self.draw_option("q", "Back")

    def _list_rules(self) -> None:
        """List all exclusion rules."""
        self.clear_screen()
        self.draw_box("EXCLUSION RULES")

        c = self.colors

        rules = self.manager.list_rules()

        if not rules:
            print(f"  {c.colorize('No exclusion rules defined', c.DIM)}")
        else:
            print(f"  {'#':<4} {'Type':<10} {'Pattern':<25} {'Context':<10}")
            print(f"  {'-' * 55}")

            for i, rule in enumerate(rules, 1):
                context = []
                if rule.exclude_from_sync:
                    context.append("sync")
                if rule.exclude_from_export:
                    context.append("export")
                context_str = ", ".join(context)

                print(f"  [{i}] {rule.component_type:<10} {rule.pattern:<25} {context_str}")
                if rule.reason:
                    print(f"      {c.colorize(rule.reason[:50], c.DIM)}")

        self.wait_for_key()

    def _add_rule(self) -> None:
        """Add a new exclusion rule."""
        self.clear_screen()
        self.draw_box("ADD EXCLUSION RULE", "1/4")

        c = self.colors

        # Component type
        print("  Select component type to exclude:")
        print("  [1] agent")
        print("  [2] skill")
        print("  [3] plugin")
        print("  [4] command")
        print("  [5] hook")
        print("  [*] all types")

        type_choice = self.prompt()
        type_map = {
            "1": "agent",
            "2": "skill",
            "3": "plugin",
            "4": "command",
            "5": "hook",
            "*": "*",
        }
        component_type = type_map.get(type_choice, "*")

        self.clear_screen()
        self.draw_box("ADD EXCLUSION RULE", "2/4")

        print(f"  Type: {component_type}")
        print()
        print("  Enter pattern to match (supports * and ? wildcards):")
        print("  Examples:")
        print("    my-*           - Everything starting with 'my-'")
        print("    *-private      - Everything ending with '-private'")
        print("    secret-*-test  - Specific pattern")
        print()

        pattern = self.prompt_text("Pattern")
        if not pattern:
            self.print_error("Pattern required")
            self.wait_for_key()
            return

        self.clear_screen()
        self.draw_box("ADD EXCLUSION RULE", "3/4")

        print(f"  Type: {component_type}")
        print(f"  Pattern: {pattern}")
        print()

        reason = self.prompt_text("Reason (optional)")

        self.clear_screen()
        self.draw_box("ADD EXCLUSION RULE", "4/4")

        print("  Exclude from:")
        print("  [1] Both sync and export (Recommended)")
        print("  [2] Sync only")
        print("  [3] Export only")

        context_choice = self.prompt()
        exclude_sync = context_choice in ("1", "2")
        exclude_export = context_choice in ("1", "3")

        # Create rule
        rule = self.manager.add_rule(
            component_type=component_type,
            pattern=pattern,
            reason=reason,
            exclude_sync=exclude_sync,
            exclude_export=exclude_export,
        )

        self.print_success(f"Created rule: {rule.id}")
        self.wait_for_key()

    def _remove_rule(self) -> None:
        """Remove an exclusion rule."""
        self.clear_screen()
        self.draw_box("REMOVE EXCLUSION RULE")

        rules = self.manager.list_rules()

        if not rules:
            print("  No rules to remove")
            self.wait_for_key()
            return

        c = self.colors

        for i, rule in enumerate(rules, 1):
            print(f"  [{i}] {rule.component_type}: {rule.pattern}")

        print()
        choice = self.prompt("Select rule to remove")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(rules):
                rule = rules[idx]
                if self.prompt_confirm(f"Remove rule '{rule.pattern}'?", default=False):
                    if self.manager.remove_rule(rule.id):
                        self.print_success("Rule removed")
                    else:
                        self.print_error("Failed to remove rule")
        except ValueError:
            pass

        self.wait_for_key()

    def _preview_exclusions(self) -> None:
        """Preview what components would be excluded."""
        self.clear_screen()
        self.draw_box("EXCLUSION PREVIEW")

        c = self.colors

        # Check agents
        self.draw_section("Agents:")
        for agent in self.syncer.agents:
            if self.manager.is_excluded("agent", agent.name):
                reason = self.manager.get_exclusion_reason("agent", agent.name)
                print(f"  {c.colorize('[EXCLUDED]', c.RED)} {agent.name}")
                if reason:
                    print(f"    {c.colorize(reason, c.DIM)}")
            else:
                print(f"  {c.colorize('[included]', c.GREEN)} {agent.name}")

        # Check skills
        self.draw_section("Skills:")
        for skill in self.syncer.skills[:10]:  # Limit display
            if self.manager.is_excluded("skill", skill.name):
                print(f"  {c.colorize('[EXCLUDED]', c.RED)} {skill.name}")
            else:
                print(f"  {c.colorize('[included]', c.GREEN)} {skill.name}")

        if len(self.syncer.skills) > 10:
            print(f"  ... and {len(self.syncer.skills) - 10} more")

        # Check plugins
        self.draw_section("Plugins:")
        for plugin in self.syncer.plugins:
            if self.manager.is_excluded("plugin", plugin.name):
                print(f"  {c.colorize('[EXCLUDED]', c.RED)} {plugin.name}")
            else:
                print(f"  {c.colorize('[included]', c.GREEN)} {plugin.name}")

        self.wait_for_key()

    def _import_export(self) -> None:
        """Import or export exclusion rules."""
        self.clear_screen()
        self.draw_box("IMPORT/EXPORT RULES")

        print("  [1] Export rules to file")
        print("  [2] Import rules from file")

        choice = self.prompt()

        if choice == "1":
            import json
            rules_data = self.manager.export_rules()
            output_path = Path.cwd() / "exclusion-rules.json"
            output_path.write_text(json.dumps(rules_data, indent=2))
            self.print_success(f"Exported to {output_path}")

        elif choice == "2":
            path = self.prompt_text("Path to rules file")
            if path:
                import json
                try:
                    rules_data = json.loads(Path(path).expanduser().read_text())
                    merge = self.prompt_confirm("Merge with existing rules?")
                    count = self.manager.import_rules(rules_data, merge=merge)
                    self.print_success(f"Imported {count} rules")
                except Exception as e:
                    self.print_error(f"Import failed: {e}")

        self.wait_for_key()
