"""Sync Menu for platform synchronization."""

from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu


class SyncMenu(BaseMenu):
    """Interactive platform sync menu."""

    PLATFORMS = [
        # SKILL.md compatible
        ("codex", "Codex CLI", "~/.codex/skills/", True),
        ("gemini", "Gemini CLI", "~/.gemini/skills/", True),
        ("antigravity", "Antigravity", "~/.gemini/antigravity/skills/", True),
        ("continue", "Continue", "~/.continue/skills/", True),
        ("opencode", "OpenCode", "~/.opencode/skills/", True),
        ("trae", "Trae", "~/.trae/skills/", True),
        # Requires conversion
        ("cursor", "Cursor", "~/.cursor/", False),
        ("windsurf", "Windsurf", "~/.windsurf/", False),
        ("roocode", "Roo Code", "~/.roo/", False),
        ("kiro", "Kiro", "~/.kiro/", False),
        ("copilot", "GitHub Copilot", "~/.github/", False),
        ("aider", "Aider", "./CONVENTIONS.md", False),
    ]

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer

    def run(self) -> Optional[str]:
        """Run the sync menu loop."""
        while True:
            self.clear_screen()
            self._draw_platform_selection()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice.lower() == 'a':
                self._sync_all()
            else:
                self._handle_selection(choice)

    def _draw_platform_selection(self) -> None:
        """Draw platform selection with status."""
        c = self.colors
        b = self.box

        self.draw_box("PLATFORM SYNC")

        print("  Select platforms (comma-separated, or 'a' for all):")
        print()

        home = Path.home()

        self.draw_section("SKILL.md Compatible:")
        idx = 1
        for platform_id, name, path, is_skill_md in self.PLATFORMS[:6]:
            full_path = Path(path.replace("~", str(home)))
            exists = full_path.exists() or full_path.parent.exists()
            skill_count = self._count_synced(full_path) if exists else 0

            indicator = c.colorize(b['check'], c.GREEN) if exists else c.colorize(b['cross_mark'], c.RED)
            status = c.colorize("installed", c.GREEN) if exists else c.colorize("not found", c.DIM)

            detail = ""
            if exists and skill_count > 0:
                detail = f"  {c.colorize(f'{skill_count} skills synced', c.DIM)}"

            print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {name:<18} {indicator} {status}{detail}")
            idx += 1

        self.draw_section("Requires Conversion:")
        for platform_id, name, path, is_skill_md in self.PLATFORMS[6:]:
            full_path = Path(path.replace("~", str(home)).replace(".", str(Path.cwd())))
            exists = full_path.exists() or full_path.parent.exists()

            indicator = c.colorize(b['check'], c.GREEN) if exists else c.colorize(b['cross_mark'], c.RED)
            status = c.colorize("installed", c.GREEN) if exists else c.colorize("not found", c.DIM)

            print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {name:<18} {indicator} {status}")
            idx += 1

        print()
        print(f"  {c.colorize('[a] Sync all', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _count_synced(self, path: Path) -> int:
        """Count synced skills in a path."""
        if not path.exists():
            return 0
        return sum(1 for d in path.iterdir() if d.is_dir() and (d / "SKILL.md").exists())

    def _handle_selection(self, choice: str) -> None:
        """Handle platform selection."""
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_platforms = [self.PLATFORMS[i] for i in indices if 0 <= i < len(self.PLATFORMS)]

            if not selected_platforms:
                self.print_error("Invalid selection")
                self.wait_for_key()
                return

            self._sync_selected(selected_platforms)
        except ValueError:
            self.print_error("Invalid input")
            self.wait_for_key()

    def _sync_selected(self, platforms: list) -> None:
        """Sync to selected platforms."""
        c = self.colors

        self.clear_screen()
        self.draw_box("SYNC CONFIRMATION")

        print("  Will sync to:")
        for _, name, path, _ in platforms:
            print(f"    - {name} ({path})")

        print()
        print("  Components to sync:")
        print(f"    - {len(self.syncer.agents)} agents")
        print(f"    - {len(self.syncer.skills)} skills")
        print(f"    - {len(self.syncer.commands)} commands")
        print(f"    - {len(self.syncer.hooks)} hooks")
        print(f"    - {len(self.syncer.mcp_config)} MCP servers")

        if not self.prompt_confirm("\n  Proceed with sync?"):
            self.print_info("Sync cancelled")
            self.wait_for_key()
            return

        print()

        for platform_id, name, path, is_skill_md in platforms:
            print(f"  Syncing to {name}...")
            try:
                self.syncer.sync_platform(platform_id)
                self.print_success(f"Synced to {name}")
            except Exception as e:
                self.print_error(f"Failed to sync to {name}: {e}")

        print()
        self.print_success("Sync complete!")
        self.wait_for_key()

    def _sync_all(self) -> None:
        """Sync to all platforms."""
        c = self.colors

        self.clear_screen()
        self.draw_box("SYNC ALL PLATFORMS")

        print("  Will sync to ALL platforms:")
        for _, name, _, _ in self.PLATFORMS:
            print(f"    - {name}")

        print()
        print("  Components to sync:")
        print(f"    - {len(self.syncer.agents)} agents")
        print(f"    - {len(self.syncer.skills)} skills")
        print(f"    - {len(self.syncer.commands)} commands")
        print(f"    - {len(self.syncer.hooks)} hooks")
        print(f"    - {len(self.syncer.mcp_config)} MCP servers")

        if not self.prompt_confirm("\n  Proceed with sync?"):
            self.print_info("Sync cancelled")
            self.wait_for_key()
            return

        print()

        for platform_id, name, _, _ in self.PLATFORMS:
            print(f"  Syncing to {name}...")
            try:
                self.syncer.sync_platform(platform_id)
                self.print_success(f"Synced to {name}")
            except Exception as e:
                self.print_error(f"Failed to sync to {name}: {e}")

        self.syncer.save_sync_state()
        print()
        self.print_success("Full sync complete!")
        self.wait_for_key()
