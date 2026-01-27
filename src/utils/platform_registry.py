"""
Consolidated Platform Registry - Single source of truth for all platform metadata.
Used by both sync_agents.py and verify_platforms.py.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PlatformConfig:
    """Complete platform configuration and metadata."""
    id: str
    name: str
    skill_format: str
    frontmatter: bool
    cli_check: Optional[str]
    global_config: Optional[Path]
    skills_path: Optional[Path]
    hooks_path: Optional[Path]
    mcp_path: Optional[Path]
    docs_url: str
    changelog_url: str = ""
    features: list[str] = field(default_factory=list)


class PlatformRegistry:
    """
    Central registry for all supported AI coding platforms.
    Provides consistent platform metadata across the codebase.
    """

    def __init__(self):
        self.home = Path.home()
        self._platforms: dict[str, PlatformConfig] = {}
        self._init_platforms()

    def _init_platforms(self) -> None:
        """Initialize all platform configurations."""

        # SKILL.md Compatible Platforms
        self._platforms["claude"] = PlatformConfig(
            id="claude",
            name="Claude Code",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check="claude --version",
            global_config=self.home / ".claude",
            skills_path=self.home / ".claude" / "skills",
            hooks_path=self.home / ".claude" / "settings.json",
            mcp_path=self.home / ".claude" / ".mcp.json",
            docs_url="https://docs.anthropic.com/en/docs/claude-code",
            changelog_url="https://docs.anthropic.com/en/docs/claude-code/changelog",
            features=["skills", "agents", "hooks", "mcp", "commands", "plugins"],
        )

        self._platforms["codex"] = PlatformConfig(
            id="codex",
            name="Codex CLI",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check="codex --version",
            global_config=self.home / ".codex",
            skills_path=self.home / ".codex" / "skills",
            hooks_path=None,
            mcp_path=None,
            docs_url="https://github.com/openai/codex",
            changelog_url="https://github.com/openai/codex/releases",
            features=["skills", "agents"],
        )

        self._platforms["gemini"] = PlatformConfig(
            id="gemini",
            name="Gemini CLI",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check="gemini --version",
            global_config=self.home / ".gemini",
            skills_path=self.home / ".gemini" / "skills",
            hooks_path=self.home / ".gemini" / "hooks.json",
            mcp_path=self.home / ".gemini" / "settings.json",
            docs_url="https://googlegemini.github.io/gemini-cli/docs/",
            changelog_url="https://github.com/anthropics/gemini-cli/releases",
            features=["skills", "extensions", "hooks", "mcp", "commands"],
        )

        self._platforms["antigravity"] = PlatformConfig(
            id="antigravity",
            name="Antigravity",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check="antigravity --version",
            global_config=self.home / ".gemini" / "antigravity",
            skills_path=self.home / ".gemini" / "antigravity" / "skills",
            hooks_path=self.home / ".gemini" / "antigravity" / "hooks.json",
            mcp_path=self.home / ".gemini" / "antigravity" / "settings.json",
            docs_url="https://github.com/anthropics/antigravity",
            changelog_url="https://github.com/anthropics/antigravity/releases",
            features=["skills", "hooks", "mcp"],
        )

        self._platforms["opencode"] = PlatformConfig(
            id="opencode",
            name="OpenCode",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check="opencode --version",
            global_config=self.home / ".opencode",
            skills_path=self.home / ".opencode" / "skills",
            hooks_path=None,
            mcp_path=None,
            docs_url="https://github.com/opencode-ai/opencode",
            changelog_url="https://github.com/opencode-ai/opencode/releases",
            features=["skills"],
        )

        self._platforms["trae"] = PlatformConfig(
            id="trae",
            name="Trae",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check="trae --version",
            global_config=self.home / ".trae",
            skills_path=self.home / ".trae" / "skills",
            hooks_path=None,
            mcp_path=None,
            docs_url="https://github.com/anthropic/trae",
            changelog_url="https://github.com/anthropic/trae/releases",
            features=["skills"],
        )

        self._platforms["continue"] = PlatformConfig(
            id="continue",
            name="Continue",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check=None,
            global_config=self.home / ".continue",
            skills_path=self.home / ".continue" / "skills",
            hooks_path=None,
            mcp_path=self.home / ".continue" / "config.json",
            docs_url="https://docs.continue.dev/",
            changelog_url="https://github.com/continuedev/continue/releases",
            features=["skills", "mcp"],
        )

        # Requires Conversion Platforms
        self._platforms["cursor"] = PlatformConfig(
            id="cursor",
            name="Cursor",
            skill_format="*.md",
            frontmatter=False,
            cli_check=None,
            global_config=self.home / ".cursor",
            skills_path=self.home / ".cursor" / "rules",
            hooks_path=None,
            mcp_path=self.home / ".cursor" / "mcp.json",
            docs_url="https://docs.cursor.com/",
            changelog_url="https://changelog.cursor.com/",
            features=["rules", "commands", "mcp"],
        )

        self._platforms["windsurf"] = PlatformConfig(
            id="windsurf",
            name="Windsurf",
            skill_format="*.md",
            frontmatter=False,
            cli_check=None,
            global_config=self.home / ".windsurf",
            skills_path=self.home / ".windsurf" / "workflows",
            hooks_path=None,
            mcp_path=self.home / ".windsurf" / "mcp_config.json",
            docs_url="https://docs.windsurf.com/",
            changelog_url="https://docs.windsurf.com/changelog",
            features=["workflows", "rules", "mcp"],
        )

        self._platforms["roocode"] = PlatformConfig(
            id="roocode",
            name="Roo Code",
            skill_format="*.md",
            frontmatter=False,
            cli_check=None,
            global_config=self.home / ".roo",
            skills_path=self.home / ".roo" / "rules",
            hooks_path=None,
            mcp_path=self.home / ".roo" / "mcp.json",
            docs_url="https://docs.roocode.com/",
            changelog_url="https://github.com/roocode/roo-code/releases",
            features=["rules", "commands", "mcp", "modes"],
        )

        self._platforms["kiro"] = PlatformConfig(
            id="kiro",
            name="Kiro",
            skill_format="*.md",
            frontmatter=False,
            cli_check="kiro --version",
            global_config=self.home / ".kiro",
            skills_path=self.home / ".kiro" / "steering",
            hooks_path=self.home / ".kiro" / "hooks",
            mcp_path=self.home / ".kiro" / "mcp.json",
            docs_url="https://kiro.dev/docs/",
            changelog_url="https://kiro.dev/changelog/",
            features=["steering", "agents", "hooks", "mcp"],
        )

        self._platforms["copilot"] = PlatformConfig(
            id="copilot",
            name="GitHub Copilot",
            skill_format="*.prompt.md",
            frontmatter=False,
            cli_check="gh copilot --version",
            global_config=self.home / ".github",
            skills_path=self.home / ".github" / "prompts",
            hooks_path=None,
            mcp_path=None,
            docs_url="https://docs.github.com/en/copilot",
            changelog_url="https://github.blog/changelog/label/copilot/",
            features=["prompts", "instructions"],
        )

        self._platforms["aider"] = PlatformConfig(
            id="aider",
            name="Aider",
            skill_format="CONVENTIONS.md",
            frontmatter=False,
            cli_check="aider --version",
            global_config=self.home / ".aider.conf.yml",
            skills_path=None,
            hooks_path=None,
            mcp_path=None,
            docs_url="https://aider.chat/docs/",
            changelog_url="https://aider.chat/HISTORY.html",
            features=["conventions", "config"],
        )

        self._platforms["codebuddy"] = PlatformConfig(
            id="codebuddy",
            name="CodeBuddy",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check=None,
            global_config=self.home / ".codebuddy",
            skills_path=self.home / ".codebuddy" / "skills",
            hooks_path=None,
            mcp_path=None,
            docs_url="",
            changelog_url="",
            features=["skills"],
        )

        self._platforms["agent"] = PlatformConfig(
            id="agent",
            name="Agent",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check=None,
            global_config=self.home / ".agent",
            skills_path=self.home / ".agent" / "skills",
            hooks_path=None,
            mcp_path=None,
            docs_url="",
            changelog_url="",
            features=["skills"],
        )

        self._platforms["qoder"] = PlatformConfig(
            id="qoder",
            name="Qoder",
            skill_format="SKILL.md",
            frontmatter=True,
            cli_check=None,
            global_config=self.home / ".qoder",
            skills_path=self.home / ".qoder" / "skills",
            hooks_path=None,
            mcp_path=None,
            docs_url="",
            changelog_url="",
            features=["skills"],
        )

    def get(self, platform_id: str) -> Optional[PlatformConfig]:
        """Get a platform configuration by ID."""
        return self._platforms.get(platform_id)

    def all(self) -> dict[str, PlatformConfig]:
        """Get all platform configurations."""
        return self._platforms.copy()

    def skill_md_compatible(self) -> list[PlatformConfig]:
        """Get platforms that support SKILL.md format."""
        return [p for p in self._platforms.values() if p.skill_format == "SKILL.md"]

    def requires_conversion(self) -> list[PlatformConfig]:
        """Get platforms that require format conversion."""
        return [p for p in self._platforms.values() if p.skill_format != "SKILL.md"]

    def installed(self) -> list[PlatformConfig]:
        """Get platforms that appear to be installed."""
        import subprocess

        installed = []
        for p in self._platforms.values():
            if p.global_config and p.global_config.exists():
                installed.append(p)
            elif p.cli_check:
                try:
                    result = subprocess.run(
                        p.cli_check.split(),
                        capture_output=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        installed.append(p)
                except Exception:
                    pass
        return installed

    def get_sync_platforms_dict(self) -> dict:
        """Get platforms dict for backward compatibility with sync_agents.py PLATFORMS."""
        return {
            p.id: {
                "name": p.name,
                "skill_format": p.skill_format,
                "frontmatter": p.frontmatter,
            }
            for p in self._platforms.values()
        }

    def get_verify_platforms_dict(self) -> dict:
        """Get platforms dict for backward compatibility with verify_platforms.py."""
        return {
            p.id: {
                "name": p.name,
                "cli_check": p.cli_check,
                "global_config": p.global_config,
                "skills": p.skills_path,
                "hooks": p.hooks_path,
                "mcp": p.mcp_path,
                "docs_url": p.docs_url,
            }
            for p in self._platforms.values()
        }


# Singleton instance
_registry = None


def get_registry() -> PlatformRegistry:
    """Get the global platform registry instance."""
    global _registry
    if _registry is None:
        _registry = PlatformRegistry()
    return _registry
