#!/usr/bin/env python3
"""
Agent Sync Script
Synchronizes Claude Code agents, skills, and plugins to other AI CLI platforms.
Supports: Gemini CLI, Antigravity, Codex CLI
"""

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AgentInfo:
    """Parsed agent information from a Claude Code agent file."""
    name: str
    description: str
    tools: list[str]
    model: str
    color: str
    content: str
    source_path: Path


@dataclass
class SkillInfo:
    """Parsed skill information from a Claude Code skill directory."""
    name: str
    description: str
    content: str
    source_path: Path
    has_scripts: bool
    has_references: bool
    has_assets: bool


class AgentSync:
    """Main sync orchestrator for cross-platform agent management."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.home = Path.home()

        # Source paths (Claude Code)
        self.claude_dir = self.home / ".claude"
        self.claude_agents = self.claude_dir / "agents"
        self.claude_skills = self.claude_dir / "skills"
        self.claude_hooks = self.claude_dir / "hooks"
        self.claude_md = self.claude_dir / "CLAUDE.md"

        # Target paths
        self.gemini_dir = self.home / ".gemini"
        self.antigravity_dir = self.gemini_dir / "antigravity"
        self.codex_dir = self.home / ".codex"

        # Sync state
        self.sync_log_path = self.claude_dir / ".agent_sync_state.json"
        self.agents: list[AgentInfo] = []
        self.skills: list[SkillInfo] = []

    def log(self, msg: str, level: str = "info"):
        """Print log message with appropriate formatting."""
        prefix = {
            "info": "ℹ️ ",
            "success": "✅",
            "warning": "⚠️ ",
            "error": "❌",
            "dry": "🔍"
        }.get(level, "  ")
        print(f"{prefix} {msg}")

    def parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        frontmatter = {}
        for line in parts[1].strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                # Handle list values (tools)
                if value.startswith("[") or ", " in value:
                    value = [v.strip().strip('"\'') for v in value.strip("[]").split(",")]
                frontmatter[key] = value

        return frontmatter, parts[2].strip()

    def load_agents(self) -> list[AgentInfo]:
        """Load all Claude Code agents."""
        agents = []
        if not self.claude_agents.exists():
            self.log(f"Agents directory not found: {self.claude_agents}", "warning")
            return agents

        for agent_file in self.claude_agents.glob("*.md"):
            try:
                content = agent_file.read_text()
                frontmatter, body = self.parse_frontmatter(content)

                agents.append(AgentInfo(
                    name=frontmatter.get("name", agent_file.stem),
                    description=frontmatter.get("description", ""),
                    tools=frontmatter.get("tools", []) if isinstance(frontmatter.get("tools"), list) else [frontmatter.get("tools", "")],
                    model=frontmatter.get("model", "sonnet"),
                    color=frontmatter.get("color", "#000000"),
                    content=body,
                    source_path=agent_file
                ))
                if self.verbose:
                    self.log(f"Loaded agent: {frontmatter.get('name', agent_file.stem)}")
            except Exception as e:
                self.log(f"Failed to load agent {agent_file}: {e}", "error")

        self.agents = agents
        return agents

    def load_skills(self) -> list[SkillInfo]:
        """Load all Claude Code skills."""
        skills = []
        if not self.claude_skills.exists():
            self.log(f"Skills directory not found: {self.claude_skills}", "warning")
            return skills

        for skill_dir in self.claude_skills.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                content = skill_md.read_text()
                frontmatter, body = self.parse_frontmatter(content)

                skills.append(SkillInfo(
                    name=frontmatter.get("name", skill_dir.name),
                    description=frontmatter.get("description", ""),
                    content=body,
                    source_path=skill_dir,
                    has_scripts=(skill_dir / "scripts").exists(),
                    has_references=(skill_dir / "references").exists(),
                    has_assets=(skill_dir / "assets").exists()
                ))
                if self.verbose:
                    self.log(f"Loaded skill: {frontmatter.get('name', skill_dir.name)}")
            except Exception as e:
                self.log(f"Failed to load skill {skill_dir}: {e}", "error")

        self.skills = skills
        return skills

    def _sync_skills_to_directory(self, target_skills_dir: Path, target_name: str):
        """Sync skills to a target directory (shared logic for Gemini/Antigravity)."""
        if not self.dry_run:
            target_skills_dir.mkdir(parents=True, exist_ok=True)

        # Sync skills (direct copy - formats are compatible)
        for skill in self.skills:
            target_dir = target_skills_dir / skill.name
            if self.dry_run:
                self.log(f"Would copy skill: {skill.name} -> {target_dir}", "dry")
            else:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(skill.source_path, target_dir)
                self.log(f"Copied skill ({target_name}): {skill.name}", "success")

        # Convert agents to skills
        agents_as_skills = target_skills_dir / "_claude_agents"
        if not self.dry_run:
            agents_as_skills.mkdir(parents=True, exist_ok=True)

        for agent in self.agents:
            agent_skill_dir = agents_as_skills / agent.name
            if self.dry_run:
                self.log(f"Would create agent-skill: {agent.name}", "dry")
            else:
                agent_skill_dir.mkdir(parents=True, exist_ok=True)

                # Create SKILL.md from agent with proper YAML formatting
                desc = agent.description
                if isinstance(desc, list):
                    desc = " ".join(desc)
                # Escape special characters and format as proper YAML
                desc = desc.replace('"', '\\"').replace('\n', ' ')

                skill_content = f"""---
name: {agent.name}
description: "{desc}"
---

{agent.content}
"""
                (agent_skill_dir / "SKILL.md").write_text(skill_content)
                self.log(f"Created agent-skill ({target_name}): {agent.name}", "success")

    def sync_to_gemini(self):
        """Sync agents and skills to Gemini CLI and Antigravity."""
        self.log("Syncing to Gemini CLI...", "info")

        # Sync to Gemini CLI (~/.gemini/skills/)
        gemini_skills = self.gemini_dir / "skills"
        self._sync_skills_to_directory(gemini_skills, "Gemini CLI")

        # Sync to Antigravity (~/.gemini/antigravity/skills/)
        self.log("Syncing to Antigravity...", "info")
        antigravity_skills = self.antigravity_dir / "skills"
        self._sync_skills_to_directory(antigravity_skills, "Antigravity")

        # Generate consolidated GEMINI.md
        gemini_md_content = self._generate_gemini_md()
        gemini_md_path = self.gemini_dir / "GEMINI.md"

        if self.dry_run:
            self.log(f"Would write GEMINI.md ({len(gemini_md_content)} chars)", "dry")
        else:
            # Backup existing if present
            if gemini_md_path.exists():
                backup = gemini_md_path.with_suffix(".md.backup")
                shutil.copy(gemini_md_path, backup)
                self.log(f"Backed up existing GEMINI.md", "info")

            gemini_md_path.write_text(gemini_md_content)
            self.log(f"Generated GEMINI.md", "success")

    def _generate_gemini_md(self) -> str:
        """Generate consolidated GEMINI.md from Claude Code config."""
        sections = []

        # Header
        sections.append(f"""# Gemini CLI Configuration
> Auto-generated from Claude Code config on {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Source: ~/.claude/

""")

        # Include CLAUDE.md content if exists
        if self.claude_md.exists():
            claude_content = self.claude_md.read_text()
            sections.append("## Global Instructions (from CLAUDE.md)\n\n")
            sections.append(claude_content)
            sections.append("\n\n")

        # Agent summaries
        if self.agents:
            sections.append("## Available Agents\n\n")
            sections.append("| Agent | Description | Model |\n")
            sections.append("|-------|-------------|-------|\n")
            for agent in self.agents:
                desc = agent.description[:80] + "..." if len(agent.description) > 80 else agent.description
                sections.append(f"| {agent.name} | {desc} | {agent.model} |\n")
            sections.append("\n")

        # Skill summaries
        if self.skills:
            sections.append("## Available Skills\n\n")
            for skill in self.skills:
                sections.append(f"### {skill.name}\n")
                sections.append(f"{skill.description}\n\n")

        return "".join(sections)

    def sync_to_codex(self):
        """Sync agents to Codex CLI."""
        self.log("Syncing to Codex CLI...", "info")

        if not self.dry_run:
            self.codex_dir.mkdir(parents=True, exist_ok=True)

        # Generate consolidated AGENTS.md
        agents_md_content = self._generate_agents_md()
        agents_md_path = self.codex_dir / "AGENTS.md"

        if self.dry_run:
            self.log(f"Would write AGENTS.md ({len(agents_md_content)} chars)", "dry")
        else:
            # Backup existing if present
            if agents_md_path.exists():
                backup = agents_md_path.with_suffix(".md.backup")
                shutil.copy(agents_md_path, backup)
                self.log(f"Backed up existing AGENTS.md", "info")

            agents_md_path.write_text(agents_md_content)
            self.log(f"Generated AGENTS.md", "success")

        # Generate config.toml suggestions
        config_suggestions = self._generate_codex_config()
        config_path = self.codex_dir / "config.toml.suggested"

        if self.dry_run:
            self.log(f"Would write config.toml.suggested", "dry")
        else:
            config_path.write_text(config_suggestions)
            self.log(f"Generated config.toml.suggested (review and merge manually)", "success")

    def _generate_agents_md(self) -> str:
        """Generate consolidated AGENTS.md for Codex CLI."""
        sections = []

        # Header
        sections.append(f"""# Codex CLI Agent Instructions
> Auto-generated from Claude Code config on {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Source: ~/.claude/

""")

        # Include CLAUDE.md content if exists
        if self.claude_md.exists():
            claude_content = self.claude_md.read_text()
            sections.append("## Global Instructions\n\n")
            sections.append(claude_content)
            sections.append("\n\n---\n\n")

        # Add each agent's content
        if self.agents:
            sections.append("## Specialized Agent Instructions\n\n")
            sections.append("The following sections contain specialized instructions for different types of tasks.\n\n")

            for agent in sorted(self.agents, key=lambda a: a.name):
                sections.append(f"### {agent.name.replace('-', ' ').title()}\n\n")
                sections.append(f"**Purpose**: {agent.description}\n\n")

                # Include condensed version of agent content
                # Codex AGENTS.md should be more concise
                content_lines = agent.content.split("\n")
                condensed = []
                in_code_block = False

                for line in content_lines[:100]:  # Limit content per agent
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                    condensed.append(line)

                sections.append("\n".join(condensed))
                sections.append("\n\n---\n\n")

        return "".join(sections)

    def _generate_codex_config(self) -> str:
        """Generate suggested config.toml for Codex CLI."""
        return f"""# Codex CLI Configuration
# Auto-generated suggestions from Claude Code sync on {datetime.now().strftime('%Y-%m-%d %H:%M')}
# Review and merge into your existing ~/.codex/config.toml

# Model configuration
model = "o4-mini"  # or "gpt-4o", "o3", etc.

# Approval mode
approval_mode = "suggest"  # "suggest", "auto-edit", or "full-auto"

# Custom instruction discovery
project_doc_fallback_filenames = ["AGENTS.md", "CLAUDE.md", "TEAM_GUIDE.md"]

# Features
[features]
shell_snapshot = true
web_search_request = true
"""

    def save_sync_state(self):
        """Save sync state for tracking."""
        state = {
            "last_sync": datetime.now().isoformat(),
            "agents_synced": [a.name for a in self.agents],
            "skills_synced": [s.name for s in self.skills],
            "platforms": ["gemini", "codex"]
        }

        if not self.dry_run:
            self.sync_log_path.write_text(json.dumps(state, indent=2))

    def list_components(self):
        """List all components that would be synced."""
        self.load_agents()
        self.load_skills()

        print("\n📦 Claude Code Components to Sync\n")
        print("=" * 50)

        print(f"\n🤖 Agents ({len(self.agents)}):")
        for agent in sorted(self.agents, key=lambda a: a.name):
            print(f"   • {agent.name}: {agent.description[:60]}...")

        print(f"\n🛠️  Skills ({len(self.skills)}):")
        for skill in sorted(self.skills, key=lambda s: s.name):
            extras = []
            if skill.has_scripts:
                extras.append("scripts")
            if skill.has_references:
                extras.append("refs")
            if skill.has_assets:
                extras.append("assets")
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            print(f"   • {skill.name}: {skill.description[:50]}...{extra_str}")

        print("\n" + "=" * 50)
        print(f"Total: {len(self.agents)} agents, {len(self.skills)} skills")

    def sync_all(self):
        """Sync to all supported platforms."""
        self.load_agents()
        self.load_skills()

        self.log(f"Found {len(self.agents)} agents, {len(self.skills)} skills")

        self.sync_to_gemini()
        self.sync_to_codex()
        self.save_sync_state()

        self.log("Sync complete!", "success")


def main():
    parser = argparse.ArgumentParser(
        description="Sync Claude Code agents and skills to other AI CLI platforms"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Sync to all supported platforms"
    )
    parser.add_argument(
        "--platform", "-p",
        choices=["gemini", "codex"],
        help="Sync to specific platform"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List components that would be synced"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without applying"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    syncer = AgentSync(dry_run=args.dry_run, verbose=args.verbose)

    if args.list:
        syncer.list_components()
    elif args.all:
        syncer.sync_all()
    elif args.platform == "gemini":
        syncer.load_agents()
        syncer.load_skills()
        syncer.sync_to_gemini()
        syncer.save_sync_state()
    elif args.platform == "codex":
        syncer.load_agents()
        syncer.load_skills()
        syncer.sync_to_codex()
        syncer.save_sync_state()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
