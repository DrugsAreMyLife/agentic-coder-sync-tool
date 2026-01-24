#!/usr/bin/env python3
"""
Platform Verification Script
Checks platform configurations, paths, and documentation status.
Run this periodically to ensure the sync tool is up to date.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class PlatformCheck:
    name: str
    installed: bool
    config_exists: bool
    skills_path: Optional[Path]
    skills_count: int
    hooks_exists: bool
    mcp_exists: bool
    notes: str = ""


# Platform definitions with paths to check
PLATFORMS = {
    "claude": {
        "name": "Claude Code",
        "cli_check": "claude --version",
        "global_config": Path.home() / ".claude",
        "skills": Path.home() / ".claude" / "skills",
        "hooks": Path.home() / ".claude" / "hooks.json",
        "mcp": Path.home() / ".claude" / ".mcp.json",
        "docs_url": "https://docs.anthropic.com/en/docs/claude-code",
    },
    "codex": {
        "name": "Codex CLI",
        "cli_check": "codex --version",
        "global_config": Path.home() / ".codex",
        "skills": Path.home() / ".codex" / "skills",
        "hooks": None,
        "mcp": None,
        "docs_url": "https://github.com/openai/codex",
    },
    "gemini": {
        "name": "Gemini CLI",
        "cli_check": "gemini --version",
        "global_config": Path.home() / ".gemini",
        "skills": Path.home() / ".gemini" / "skills",
        "hooks": Path.home() / ".gemini" / "hooks.json",
        "mcp": Path.home() / ".gemini" / "settings.json",
        "docs_url": "https://googlegemini.github.io/gemini-cli/docs/",
    },
    "antigravity": {
        "name": "Antigravity",
        "cli_check": "antigravity --version",
        "global_config": Path.home() / ".gemini" / "antigravity",
        "skills": Path.home() / ".gemini" / "antigravity" / "skills",
        "hooks": Path.home() / ".gemini" / "antigravity" / "hooks.json",
        "mcp": Path.home() / ".gemini" / "antigravity" / "settings.json",
        "docs_url": "https://github.com/anthropics/antigravity",
    },
    "cursor": {
        "name": "Cursor",
        "cli_check": None,  # GUI app
        "global_config": Path.home() / ".cursor",
        "skills": Path.home() / ".cursor" / "rules",
        "hooks": None,
        "mcp": Path.home() / ".cursor" / "mcp.json",
        "docs_url": "https://docs.cursor.com/",
    },
    "windsurf": {
        "name": "Windsurf",
        "cli_check": None,  # GUI app
        "global_config": Path.home() / ".windsurf",
        "skills": Path.home() / ".windsurf" / "workflows",
        "hooks": None,
        "mcp": Path.home() / ".windsurf" / "mcp_config.json",
        "docs_url": "https://docs.windsurf.com/",
    },
    "roocode": {
        "name": "Roo Code",
        "cli_check": None,  # VS Code extension
        "global_config": Path.home() / ".roo",
        "skills": None,  # Project-level only
        "hooks": None,
        "mcp": Path.home() / ".roo" / "mcp.json",
        "docs_url": "https://docs.roocode.com/",
    },
    "kiro": {
        "name": "Kiro",
        "cli_check": "kiro --version",
        "global_config": Path.home() / ".kiro",
        "skills": Path.home() / ".kiro" / "steering",
        "hooks": Path.home() / ".kiro" / "hooks",
        "mcp": Path.home() / ".kiro" / "mcp.json",
        "docs_url": "https://kiro.dev/docs/",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "cli_check": "gh copilot --version",
        "global_config": None,  # Project-level only
        "skills": None,
        "hooks": None,
        "mcp": None,
        "docs_url": "https://docs.github.com/en/copilot",
    },
    "continue": {
        "name": "Continue",
        "cli_check": None,  # IDE extension
        "global_config": Path.home() / ".continue",
        "skills": Path.home() / ".continue" / "skills",
        "hooks": None,
        "mcp": Path.home() / ".continue" / "config.json",
        "docs_url": "https://docs.continue.dev/",
    },
    "opencode": {
        "name": "OpenCode",
        "cli_check": "opencode --version",
        "global_config": Path.home() / ".opencode",
        "skills": Path.home() / ".opencode" / "skills",
        "hooks": None,
        "mcp": None,
        "docs_url": "https://github.com/opencode-ai/opencode",
    },
    "trae": {
        "name": "Trae",
        "cli_check": "trae --version",
        "global_config": Path.home() / ".trae",
        "skills": Path.home() / ".trae" / "skills",
        "hooks": None,
        "mcp": None,
        "docs_url": "https://github.com/anthropic/trae",
    },
    "aider": {
        "name": "Aider",
        "cli_check": "aider --version",
        "global_config": Path.home() / ".aider.conf.yml",
        "skills": None,  # Uses CONVENTIONS.md in project
        "hooks": None,
        "mcp": None,
        "docs_url": "https://aider.chat/docs/",
    },
}


def check_cli_installed(cmd: Optional[str]) -> bool:
    """Check if a CLI tool is installed."""
    if not cmd:
        return False
    try:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def count_skills(skills_path: Optional[Path]) -> int:
    """Count skill files in a directory."""
    if not skills_path or not skills_path.exists():
        return 0

    count = 0
    for ext in ["*.md", "*.yaml", "*.yml", "*.json"]:
        count += len(list(skills_path.glob(ext)))
    return count


def check_platform(platform_id: str, config: dict) -> PlatformCheck:
    """Check a single platform's status."""
    cli_installed = check_cli_installed(config.get("cli_check"))

    global_config = config.get("global_config")
    config_exists = global_config.exists() if global_config else False

    skills_path = config.get("skills")
    skills_count = count_skills(skills_path) if skills_path else 0

    hooks_path = config.get("hooks")
    hooks_exists = hooks_path.exists() if hooks_path else False

    mcp_path = config.get("mcp")
    mcp_exists = mcp_path.exists() if mcp_path else False

    return PlatformCheck(
        name=config["name"],
        installed=cli_installed or config_exists,
        config_exists=config_exists,
        skills_path=skills_path,
        skills_count=skills_count,
        hooks_exists=hooks_exists,
        mcp_exists=mcp_exists,
    )


def print_report(checks: dict[str, PlatformCheck]) -> None:
    """Print a formatted verification report."""
    print("\n" + "=" * 70)
    print(f"PLATFORM VERIFICATION REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Summary table
    print("\n## Installation Status\n")
    print(f"{'Platform':<20} {'Installed':<12} {'Config':<10} {'Skills':<10} {'Hooks':<8} {'MCP':<8}")
    print("-" * 70)

    for platform_id, check in checks.items():
        installed = "✓" if check.installed else "✗"
        config = "✓" if check.config_exists else "✗"
        skills = str(check.skills_count) if check.skills_path else "N/A"
        hooks = "✓" if check.hooks_exists else "✗"
        mcp = "✓" if check.mcp_exists else "✗"

        print(f"{check.name:<20} {installed:<12} {config:<10} {skills:<10} {hooks:<8} {mcp:<8}")

    # Detailed paths
    print("\n## Skill Paths\n")
    for platform_id, check in checks.items():
        if check.skills_path:
            exists = "✓" if check.skills_path.exists() else "✗"
            print(f"{exists} {check.name}: {check.skills_path}")

    # Sync compatibility
    print("\n## Sync Compatibility Matrix\n")
    skill_md_platforms = ["claude", "codex", "gemini", "antigravity", "continue", "opencode", "trae"]
    print("Platforms with SKILL.md format (direct copy compatible):")
    for p in skill_md_platforms:
        if p in checks:
            status = "✓ installed" if checks[p].installed else "not installed"
            print(f"  - {checks[p].name}: {status}")

    # Recommendations
    print("\n## Recommendations\n")

    installed_count = sum(1 for c in checks.values() if c.installed)
    total_count = len(checks)
    print(f"- {installed_count}/{total_count} platforms detected")

    empty_skills = [c.name for c in checks.values() if c.skills_path and c.skills_count == 0]
    if empty_skills:
        print(f"- Empty skill directories: {', '.join(empty_skills)}")

    no_mcp = [c.name for c in checks.values() if c.installed and not c.mcp_exists and PLATFORMS.get(c.name.lower(), {}).get("mcp")]
    if no_mcp:
        print(f"- Missing MCP config: {', '.join(no_mcp)}")

    print("\n" + "=" * 70)


def export_json(checks: dict[str, PlatformCheck], output_path: Path) -> None:
    """Export results to JSON."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "platforms": {}
    }

    for platform_id, check in checks.items():
        data["platforms"][platform_id] = {
            "name": check.name,
            "installed": check.installed,
            "config_exists": check.config_exists,
            "skills_path": str(check.skills_path) if check.skills_path else None,
            "skills_count": check.skills_count,
            "hooks_exists": check.hooks_exists,
            "mcp_exists": check.mcp_exists,
        }

    output_path.write_text(json.dumps(data, indent=2))
    print(f"\nJSON report exported to: {output_path}")


def main():
    """Run platform verification."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify AI coding platform installations")
    parser.add_argument("--json", type=Path, help="Export results to JSON file")
    parser.add_argument("--platform", type=str, help="Check specific platform only")
    args = parser.parse_args()

    if args.platform:
        if args.platform not in PLATFORMS:
            print(f"Unknown platform: {args.platform}")
            print(f"Available: {', '.join(PLATFORMS.keys())}")
            sys.exit(1)
        platforms_to_check = {args.platform: PLATFORMS[args.platform]}
    else:
        platforms_to_check = PLATFORMS

    checks = {}
    for platform_id, config in platforms_to_check.items():
        checks[platform_id] = check_platform(platform_id, config)

    print_report(checks)

    if args.json:
        export_json(checks, args.json)


if __name__ == "__main__":
    main()
