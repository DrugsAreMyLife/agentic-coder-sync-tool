"""Skill Browser and Builder for managing skills."""

from pathlib import Path
from typing import Optional

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu
from utils.formatters import format_description, truncate


class SkillBrowser(BaseMenu):
    """Interactive skill browser with creation and sync capabilities."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer
        self.skills = syncer.skills
        self.search_query = ""
        self.view_mode = "categorized"  # categorized, all, search

    def run(self) -> Optional[str]:
        """Run the skill browser loop."""
        while True:
            self.clear_screen()

            if self.view_mode == "search" and self.search_query:
                self._draw_search_results()
            elif self.view_mode == "categorized":
                self._draw_categorized()
            else:
                self._draw_all()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice.lower() == 's':
                self._do_search()
            elif choice.lower() == 'a':
                self.view_mode = "all" if self.view_mode != "all" else "categorized"
            elif choice.lower() == 'n':
                self._create_skill()
            elif choice.lower() == 'i':
                self._import_skill()
            elif choice.lower() == 'c':
                self.view_mode = "categorized"
                self.search_query = ""
            elif choice.isdigit():
                idx = int(choice)
                skill = self._get_skill_by_index(idx)
                if skill:
                    self._show_skill_detail(skill)

    def _categorize_skills(self) -> dict[str, list]:
        """Categorize skills by their apparent purpose."""
        categories = {
            "Development": [],
            "Integrations": [],
            "Utilities": [],
            "Content": [],
            "Other": [],
        }

        dev_keywords = ["dev", "build", "test", "deploy", "frontend", "backend", "code", "design"]
        integration_keywords = ["fetch", "api", "sync", "mcp", "langsmith", "notebooklm", "hugging"]
        utility_keywords = ["file", "video", "download", "organiz", "invoice", "changelog"]
        content_keywords = ["content", "research", "write", "document", "resume"]

        for skill in self.skills:
            name_lower = skill.name.lower()
            desc_lower = skill.description.lower() if skill.description else ""
            combined = f"{name_lower} {desc_lower}"

            if any(kw in combined for kw in dev_keywords):
                categories["Development"].append(skill)
            elif any(kw in combined for kw in integration_keywords):
                categories["Integrations"].append(skill)
            elif any(kw in combined for kw in utility_keywords):
                categories["Utilities"].append(skill)
            elif any(kw in combined for kw in content_keywords):
                categories["Content"].append(skill)
            else:
                categories["Other"].append(skill)

        return {k: v for k, v in categories.items() if v}

    def _draw_categorized(self) -> None:
        """Draw skills grouped by category."""
        c = self.colors
        total = len(self.skills)

        self.draw_box("SKILL BROWSER", f"{total} skills loaded")

        categories = self._categorize_skills()
        idx = 1

        for category, skills in categories.items():
            self.draw_section(f"{category}:")

            for skill in skills[:5]:
                desc = format_description(skill.description, 35)
                extras = []
                if skill.has_scripts:
                    extras.append("scripts")
                if skill.has_references:
                    extras.append("refs")
                extra_str = f" [{', '.join(extras)}]" if extras else ""
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {skill.name:<25}{c.colorize(extra_str, c.DIM)}")
                idx += 1

            if len(skills) > 5:
                remaining = len(skills) - 5
                print(f"      {c.colorize(f'... and {remaining} more', c.DIM)}")

        print()
        print(f"  {c.colorize('[a] Show all', c.DIM)}  {c.colorize('[s] Search', c.DIM)}  {c.colorize('[n] New skill', c.DIM)}  {c.colorize('[i] Import', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _draw_all(self) -> None:
        """Draw all skills in a flat list."""
        c = self.colors
        total = len(self.skills)

        self.draw_box("SKILL BROWSER", f"{total} skills")

        sorted_skills = sorted(self.skills, key=lambda s: s.name)

        for idx, skill in enumerate(sorted_skills[:20], 1):
            desc = format_description(skill.description, 35)
            print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {skill.name:<25} {c.colorize(desc, c.DIM)}")

        if len(sorted_skills) > 20:
            print(f"  {c.colorize(f'... and {len(sorted_skills) - 20} more', c.DIM)}")

        print()
        print(f"  {c.colorize('[c] Categorized', c.DIM)}  {c.colorize('[s] Search', c.DIM)}  {c.colorize('[n] New skill', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _draw_search_results(self) -> None:
        """Draw search results."""
        c = self.colors

        matching = [s for s in self.skills if self.search_query.lower() in s.name.lower()
                    or self.search_query.lower() in (s.description or "").lower()]

        self.draw_box("SEARCH RESULTS", f"'{self.search_query}'")

        if not matching:
            print(f"  {c.colorize('No skills found.', c.DIM)}")
        else:
            for idx, skill in enumerate(matching[:15], 1):
                desc = format_description(skill.description, 35)
                print(f"  {c.colorize(f'[{idx}]', c.CYAN, c.BOLD)} {skill.name:<25} {c.colorize(desc, c.DIM)}")

        print()
        print(f"  {c.colorize('[c] Categorized', c.DIM)}  {c.colorize('[s] New search', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

    def _do_search(self) -> None:
        """Prompt for search query."""
        query = self.prompt_text("Search skills")
        if query:
            self.search_query = query
            self.view_mode = "search"

    def _get_skill_by_index(self, idx: int):
        """Get skill by display index based on current view."""
        if self.view_mode == "categorized":
            all_skills = []
            for skills in self._categorize_skills().values():
                all_skills.extend(skills[:5])
            if 1 <= idx <= len(all_skills):
                return all_skills[idx - 1]
        elif self.view_mode == "search":
            matching = [s for s in self.skills if self.search_query.lower() in s.name.lower()
                        or self.search_query.lower() in (s.description or "").lower()]
            if 1 <= idx <= len(matching):
                return matching[idx - 1]
        else:
            sorted_skills = sorted(self.skills, key=lambda s: s.name)
            if 1 <= idx <= len(sorted_skills):
                return sorted_skills[idx - 1]
        return None

    def _show_skill_detail(self, skill) -> None:
        """Show detailed view of a skill."""
        while True:
            self.clear_screen()
            c = self.colors
            b = self.box

            self.draw_box(f"SKILL: {skill.name}")

            # Description
            self.draw_section("DESCRIPTION")
            desc = format_description(skill.description, 200)
            print(f"  {desc}")

            # Structure
            self.draw_section("STRUCTURE")
            print(f"  {skill.source_path}/")

            skill_md = skill.source_path / "SKILL.md"
            scripts_dir = skill.source_path / "scripts"
            refs_dir = skill.source_path / "references"
            assets_dir = skill.source_path / "assets"

            status_check = c.colorize(b['check'], c.GREEN)
            status_cross = c.colorize(b['cross_mark'], c.RED)

            print(f"  {status_check if skill_md.exists() else status_cross} SKILL.md")
            print(f"  {status_check if skill.has_scripts else status_cross} scripts/       {self._count_files(scripts_dir)} files" if skill.has_scripts else f"  {status_cross} scripts/")
            print(f"  {status_check if skill.has_references else status_cross} references/   {self._count_files(refs_dir)} files" if skill.has_references else f"  {status_cross} references/")
            print(f"  {status_check if skill.has_assets else status_cross} assets/")

            # Sync status
            self.draw_section("SYNCED TO")
            home = Path.home()
            sync_targets = [
                ("Gemini CLI", home / ".gemini" / "skills" / skill.name),
                ("Codex CLI", home / ".codex" / "skills" / skill.name),
                ("Antigravity", home / ".gemini" / "antigravity" / "skills" / skill.name),
                ("Continue", home / ".continue" / "skills" / skill.name),
            ]

            for name, path in sync_targets:
                exists = path.exists()
                indicator = c.colorize(b['check'], c.GREEN) if exists else c.colorize(b['cross_mark'], c.RED)
                status = "(synced)" if exists else "(not synced)"
                print(f"  {indicator} {name:<15} {c.colorize(status, c.DIM)}")

            print()
            print(f"  {c.colorize('[e] Edit', c.DIM)}  {c.colorize('[s] Sync', c.DIM)}  {c.colorize('[d] Delete', c.DIM)}  {c.colorize('[q] Back', c.DIM)}")

            choice = self.prompt()

            if choice.lower() == 'q':
                return
            elif choice.lower() == 'e':
                self._edit_skill(skill)
            elif choice.lower() == 's':
                self._sync_skill(skill)
            elif choice.lower() == 'd':
                if self._delete_skill(skill):
                    return

    def _count_files(self, path: Path) -> int:
        """Count files in a directory."""
        if not path.exists():
            return 0
        return sum(1 for f in path.iterdir() if f.is_file())

    def _edit_skill(self, skill) -> None:
        """Edit a skill's SKILL.md file."""
        import subprocess
        skill_md = skill.source_path / "SKILL.md"

        if self.prompt_confirm(f"Open {skill_md} in editor"):
            subprocess.run(["code", str(skill_md)], check=False)
            self.print_success("Editor opened")
        else:
            self.print_info("Edit cancelled")

        self.wait_for_key()

    def _sync_skill(self, skill) -> None:
        """Sync a single skill to all platforms."""
        import shutil

        home = Path.home()
        targets = [
            home / ".gemini" / "skills" / skill.name,
            home / ".codex" / "skills" / skill.name,
            home / ".gemini" / "antigravity" / "skills" / skill.name,
            home / ".continue" / "skills" / skill.name,
        ]

        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(skill.source_path, target)
            self.print_success(f"Synced to {target}")

        self.wait_for_key()

    def _delete_skill(self, skill) -> bool:
        """Delete a skill after confirmation."""
        import shutil

        if not self.prompt_confirm(f"Delete skill '{skill.name}'?", default=False):
            return False

        shutil.rmtree(skill.source_path)
        self.print_success(f"Deleted {skill.source_path}")

        # Reload skills
        self.syncer.skills = self.syncer.load_claude_skills()
        self.skills = self.syncer.skills

        self.wait_for_key()
        return True

    def _create_skill(self) -> None:
        """Create a new skill interactively."""
        c = self.colors
        self.clear_screen()

        self.draw_box("NEW SKILL WIZARD", "1/4")

        name = self.prompt_text("Skill name (lowercase, hyphens)")
        if not name:
            return

        description = self.prompt_text("Description")
        if not description:
            description = f"Skill for {name.replace('-', ' ')} tasks"

        self.clear_screen()
        self.draw_box("NEW SKILL WIZARD", "2/4")

        print("  Include optional directories?")
        print("  [1] scripts/     - Shell/Python scripts")
        print("  [2] references/  - Documentation files")
        print("  [3] assets/      - Images, templates")
        print()
        print("  Select (comma-separated, or none):")

        dir_choice = self.prompt()
        include_scripts = "1" in dir_choice
        include_refs = "2" in dir_choice
        include_assets = "3" in dir_choice

        # Create skill directory
        skills_dir = self.syncer.claude_skills
        skills_dir.mkdir(parents=True, exist_ok=True)

        skill_path = skills_dir / name
        if skill_path.exists():
            self.print_error(f"Skill '{name}' already exists")
            self.wait_for_key()
            return

        skill_path.mkdir(parents=True)

        # Create SKILL.md
        skill_md = f"""---
name: {name}
description: "{description}"
---

# {name.replace('-', ' ').title()}

{description}

## Usage

[Describe how to use this skill]

## Examples

[Add examples here]
"""
        (skill_path / "SKILL.md").write_text(skill_md)

        # Create optional directories
        if include_scripts:
            (skill_path / "scripts").mkdir()
            (skill_path / "scripts" / ".gitkeep").touch()

        if include_refs:
            (skill_path / "references").mkdir()
            (skill_path / "references" / ".gitkeep").touch()

        if include_assets:
            (skill_path / "assets").mkdir()
            (skill_path / "assets" / ".gitkeep").touch()

        self.clear_screen()
        self.draw_box("NEW SKILL WIZARD", "4/4")

        self.print_success(f"Created {skill_path}/SKILL.md")
        if include_scripts:
            self.print_success(f"Created {skill_path}/scripts/")
        if include_refs:
            self.print_success(f"Created {skill_path}/references/")
        if include_assets:
            self.print_success(f"Created {skill_path}/assets/")

        # Reload skills
        self.syncer.skills = self.syncer.load_claude_skills()
        self.skills = self.syncer.skills

        self.wait_for_key()

    def _import_skill(self) -> None:
        """Import a skill from a URL or path."""
        c = self.colors

        print("  Import from:")
        print("  [1] Local path")
        print("  [2] Git repository URL")

        choice = self.prompt()

        if choice == "1":
            path = self.prompt_text("Path to skill directory")
            if path:
                import shutil
                src = Path(path).expanduser()
                if src.exists() and (src / "SKILL.md").exists():
                    dest = self.syncer.claude_skills / src.name
                    if dest.exists():
                        self.print_error(f"Skill '{src.name}' already exists")
                    else:
                        shutil.copytree(src, dest)
                        self.print_success(f"Imported {src.name}")
                        self.syncer.skills = self.syncer.load_claude_skills()
                        self.skills = self.syncer.skills
                else:
                    self.print_error("Invalid skill directory (must contain SKILL.md)")
        elif choice == "2":
            url = self.prompt_text("Git repository URL")
            if url:
                self.print_info("Git import not yet implemented")

        self.wait_for_key()
