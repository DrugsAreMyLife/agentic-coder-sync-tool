#!/usr/bin/env python3
"""
Agentic Coder Sync Tool
Synchronizes Claude Code agents, skills, plugins, commands, and hooks
across all major AI coding agent platforms with bidirectional support.

Supports: Claude Code, Codex CLI, Gemini CLI, Antigravity, OpenCode, Trae,
          Continue, Cursor, Windsurf, Roo Code, Kiro, GitHub Copilot, Aider
"""

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================================================================
# Constants - Available Tools by Platform
# =============================================================================

ALL_CLAUDE_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Glob", "Grep", "LS",
    "Task", "WebFetch", "WebSearch", "TodoWrite", "AskUserQuestion",
    "Skill", "NotebookEdit", "NotebookRead", "BashOutput", "KillShell",
    "EnterPlanMode", "ExitPlanMode", "TaskCreate", "TaskGet", "TaskUpdate", "TaskList"
]

# Platform registry with metadata
PLATFORMS = {
    "claude": {"name": "Claude Code", "skill_format": "SKILL.md", "frontmatter": True},
    "codex": {"name": "Codex CLI", "skill_format": "SKILL.md", "frontmatter": True},
    "gemini": {"name": "Gemini CLI", "skill_format": "SKILL.md", "frontmatter": True},
    "antigravity": {"name": "Antigravity", "skill_format": "SKILL.md", "frontmatter": True},
    "opencode": {"name": "OpenCode", "skill_format": "SKILL.md", "frontmatter": True},
    "trae": {"name": "Trae", "skill_format": "SKILL.md", "frontmatter": True},
    "continue": {"name": "Continue", "skill_format": "SKILL.md", "frontmatter": True},
    "cursor": {"name": "Cursor", "skill_format": "*.md", "frontmatter": False},
    "windsurf": {"name": "Windsurf", "skill_format": "*.md", "frontmatter": False},
    "roocode": {"name": "Roo Code", "skill_format": "*.md", "frontmatter": False},
    "kiro": {"name": "Kiro", "skill_format": "*.md", "frontmatter": False},
    "copilot": {"name": "GitHub Copilot", "skill_format": "*.prompt.md", "frontmatter": False},
    "aider": {"name": "Aider", "skill_format": "CONVENTIONS.md", "frontmatter": False},
}


# =============================================================================
# Data Classes
# =============================================================================

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
    source_platform: str = "claude"


@dataclass
class SkillInfo:
    """Parsed skill information from a skill directory."""
    name: str
    description: str
    content: str
    source_path: Path
    has_scripts: bool
    has_references: bool
    has_assets: bool
    source_platform: str = "claude"


@dataclass
class CommandInfo:
    """Parsed command/slash command information."""
    name: str
    description: str
    content: str
    source_path: Path
    allowed_tools: list[str] = field(default_factory=list)
    argument_hint: str = ""
    source_platform: str = "claude"


@dataclass
class HookInfo:
    """Parsed hook information."""
    event: str
    matcher: str
    hook_type: str
    command: str
    timeout: int = 60
    source_path: Optional[Path] = None
    source_platform: str = "claude"


@dataclass
class PluginInfo:
    """Parsed plugin/extension information."""
    name: str
    description: str
    version: str
    author: str
    source_path: Path
    has_commands: bool = False
    has_agents: bool = False
    has_skills: bool = False
    has_hooks: bool = False
    has_mcp: bool = False
    source_platform: str = "claude"


# =============================================================================
# Utility Functions
# =============================================================================

def convert_allowed_to_excluded(allowed_tools: list[str]) -> list[str]:
    """Convert Claude's allowed-tools (whitelist) to Gemini's excludeTools (blacklist)."""
    if not allowed_tools or "*" in allowed_tools:
        return []
    return [tool for tool in ALL_CLAUDE_TOOLS if tool not in allowed_tools]


def convert_excluded_to_allowed(excluded_tools: list[str]) -> list[str]:
    """Convert Gemini's excludeTools (blacklist) to Claude's allowed-tools (whitelist)."""
    if not excluded_tools:
        return ["*"]
    return [tool for tool in ALL_CLAUDE_TOOLS if tool not in excluded_tools]


def transform_mcp_paths_to_gemini(mcp_config: dict, source_dir: Path) -> dict:
    """Transform MCP server paths from Claude format to Gemini format."""
    transformed = {}
    for server_name, server_config in mcp_config.items():
        new_config = dict(server_config)
        if "args" in new_config:
            new_args = []
            for arg in new_config["args"]:
                if isinstance(arg, str) and not arg.startswith("$"):
                    if "/" in arg or arg.endswith(".js") or arg.endswith(".py"):
                        new_args.append(f"${{extensionPath}}/{arg}")
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)
            new_config["args"] = new_args
        transformed[server_name] = new_config
    return transformed


def transform_mcp_paths_to_claude(mcp_config: dict) -> dict:
    """Transform MCP server paths from Gemini format to Claude format."""
    transformed = {}
    for server_name, server_config in mcp_config.items():
        new_config = dict(server_config)
        if "args" in new_config:
            new_args = []
            for arg in new_config["args"]:
                if isinstance(arg, str):
                    arg = arg.replace("${extensionPath}/", "").replace("${extensionPath}", "")
                new_args.append(arg)
            new_config["args"] = new_args
        transformed[server_name] = new_config
    return transformed


def infer_settings_from_env(env_config: dict) -> list[dict]:
    """Infer Gemini settings schema from Claude environment variables."""
    settings = []
    secret_keywords = ["key", "secret", "token", "password", "api_key", "apikey"]
    for key, value in env_config.items():
        setting = {"name": key, "description": f"{key.replace('_', ' ').title()} configuration"}
        if any(kw in key.lower() for kw in secret_keywords):
            setting["secret"] = True
            setting["required"] = True
        if value and not value.startswith("${"):
            setting["default"] = value
        settings.append(setting)
    return settings


def strip_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return content


def extract_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown content."""
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
            if value.startswith("[") or ", " in value:
                value = [v.strip().strip('"\'') for v in value.strip("[]").split(",")]
            frontmatter[key] = value
    return frontmatter, parts[2].strip()


# =============================================================================
# Main Sync Class
# =============================================================================

class AgentSync:
    """Main sync orchestrator for cross-platform agent management."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.home = Path.home()

        # =====================================================================
        # Claude Code paths (PRIMARY SOURCE)
        # =====================================================================
        self.claude_dir = self.home / ".claude"
        self.claude_agents = self.claude_dir / "agents"
        self.claude_skills = self.claude_dir / "skills"
        self.claude_commands = self.claude_dir / "commands"
        self.claude_hooks = self.claude_dir / "hooks"
        self.claude_plugins = self.claude_dir / "plugins"
        self.claude_settings = self.claude_dir / "settings.json"
        self.claude_md = self.claude_dir / "CLAUDE.md"
        self.claude_mcp = self.claude_dir / ".mcp.json"

        # =====================================================================
        # Gemini CLI paths
        # =====================================================================
        self.gemini_dir = self.home / ".gemini"
        self.gemini_skills = self.gemini_dir / "skills"
        self.gemini_extensions = self.gemini_dir / "extensions"
        self.gemini_settings = self.gemini_dir / "settings.json"
        self.gemini_md = self.gemini_dir / "GEMINI.md"

        # =====================================================================
        # Antigravity paths (within Gemini)
        # =====================================================================
        self.antigravity_dir = self.gemini_dir / "antigravity"
        self.antigravity_skills = self.antigravity_dir / "skills"

        # =====================================================================
        # Codex CLI paths
        # =====================================================================
        self.codex_dir = self.home / ".codex"
        self.codex_skills = self.codex_dir / "skills"
        self.codex_rules = self.codex_dir / "rules"
        self.codex_agents_md = self.codex_dir / "AGENTS.md"
        self.codex_config = self.codex_dir / "config.toml"

        # =====================================================================
        # OpenCode paths
        # =====================================================================
        self.opencode_dir = self.home / ".opencode"
        self.opencode_skills = self.opencode_dir / "skills"
        self.opencode_config = self.opencode_dir / "opencode.json"

        # =====================================================================
        # Trae paths
        # =====================================================================
        self.trae_dir = self.home / ".trae"
        self.trae_skills = self.trae_dir / "skills"

        # =====================================================================
        # Continue paths
        # =====================================================================
        self.continue_dir = self.home / ".continue"
        self.continue_skills = self.continue_dir / "skills"
        self.continue_mcp = self.continue_dir / "mcpServers"

        # =====================================================================
        # Cursor paths
        # =====================================================================
        self.cursor_dir = self.home / ".cursor"
        self.cursor_commands = self.cursor_dir / "commands"
        self.cursor_rules = self.cursor_dir / "rules"
        self.cursor_mcp = self.cursor_dir / "mcp.json"

        # =====================================================================
        # Windsurf paths
        # =====================================================================
        self.windsurf_dir = self.home / ".windsurf"
        self.windsurf_workflows = self.windsurf_dir / "workflows"
        self.windsurf_rules = self.windsurf_dir / "rules"

        # =====================================================================
        # Roo Code paths
        # =====================================================================
        self.roo_dir = self.home / ".roo"
        self.roo_commands = self.roo_dir / "commands"
        self.roo_rules = self.roo_dir / "rules"
        self.roo_modes = self.home / "custom_modes.yaml"

        # =====================================================================
        # Kiro paths
        # =====================================================================
        self.kiro_dir = self.home / ".kiro"
        self.kiro_steering = self.kiro_dir / "steering"
        self.kiro_settings = self.kiro_dir / "settings"
        self.kiro_mcp = self.kiro_settings / "mcp.json"

        # =====================================================================
        # GitHub Copilot paths
        # =====================================================================
        self.copilot_dir = self.home / ".github"
        self.copilot_prompts = self.copilot_dir / "prompts"
        self.copilot_instructions = self.copilot_dir / "copilot-instructions.md"

        # =====================================================================
        # Aider paths
        # =====================================================================
        self.aider_config = self.home / ".aider.conf.yml"
        self.aider_conventions = Path("CONVENTIONS.md")  # Project-level

        # =====================================================================
        # Sync state
        # =====================================================================
        self.sync_log_path = self.claude_dir / ".agent_sync_state.json"

        # Loaded components
        self.agents: list[AgentInfo] = []
        self.skills: list[SkillInfo] = []
        self.commands: list[CommandInfo] = []
        self.hooks: list[HookInfo] = []
        self.plugins: list[PluginInfo] = []
        self.mcp_config: dict = {}

    def log(self, msg: str, level: str = "info"):
        """Print log message with appropriate formatting (no emojis)."""
        prefix = {
            "info": "[*]",
            "success": "[+]",
            "warning": "[!]",
            "error": "[-]",
            "dry": "[?]",
            "sync": "[~]",
            "platform": "[>]"
        }.get(level, "   ")
        print(f"{prefix} {msg}")

    # =========================================================================
    # Claude Code Loaders
    # =========================================================================

    def load_claude_agents(self) -> list[AgentInfo]:
        """Load all Claude Code agents."""
        agents = []
        if not self.claude_agents.exists():
            return agents

        for agent_file in self.claude_agents.glob("*.md"):
            try:
                content = agent_file.read_text()
                frontmatter, body = extract_yaml_frontmatter(content)
                tools = frontmatter.get("tools", [])
                if isinstance(tools, str):
                    tools = [t.strip() for t in tools.split(",")]

                agents.append(AgentInfo(
                    name=frontmatter.get("name", agent_file.stem),
                    description=frontmatter.get("description", ""),
                    tools=tools,
                    model=frontmatter.get("model", "sonnet"),
                    color=frontmatter.get("color", "#000000"),
                    content=body,
                    source_path=agent_file,
                    source_platform="claude"
                ))
                if self.verbose:
                    self.log(f"Loaded Claude agent: {agent_file.stem}")
            except Exception as e:
                self.log(f"Failed to load agent {agent_file}: {e}", "error")
        return agents

    def load_claude_skills(self) -> list[SkillInfo]:
        """Load all Claude Code skills."""
        skills = []
        if not self.claude_skills.exists():
            return skills

        for skill_dir in self.claude_skills.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                content = skill_md.read_text()
                frontmatter, body = extract_yaml_frontmatter(content)

                skills.append(SkillInfo(
                    name=frontmatter.get("name", skill_dir.name),
                    description=frontmatter.get("description", ""),
                    content=body,
                    source_path=skill_dir,
                    has_scripts=(skill_dir / "scripts").exists(),
                    has_references=(skill_dir / "references").exists(),
                    has_assets=(skill_dir / "assets").exists(),
                    source_platform="claude"
                ))
                if self.verbose:
                    self.log(f"Loaded Claude skill: {skill_dir.name}")
            except Exception as e:
                self.log(f"Failed to load skill {skill_dir}: {e}", "error")
        return skills

    def load_claude_commands(self) -> list[CommandInfo]:
        """Load all Claude Code slash commands."""
        commands = []
        if not self.claude_commands.exists():
            return commands

        for cmd_file in self.claude_commands.glob("*.md"):
            try:
                content = cmd_file.read_text()
                frontmatter, body = extract_yaml_frontmatter(content)
                tools = frontmatter.get("allowed-tools", [])
                if isinstance(tools, str):
                    tools = [t.strip() for t in tools.split(",")]

                commands.append(CommandInfo(
                    name=cmd_file.stem,
                    description=frontmatter.get("description", ""),
                    content=body,
                    source_path=cmd_file,
                    allowed_tools=tools,
                    argument_hint=frontmatter.get("argument-hint", ""),
                    source_platform="claude"
                ))
                if self.verbose:
                    self.log(f"Loaded Claude command: /{cmd_file.stem}")
            except Exception as e:
                self.log(f"Failed to load command {cmd_file}: {e}", "error")
        return commands

    def load_claude_hooks(self) -> list[HookInfo]:
        """Load all Claude Code hooks from settings."""
        hooks = []

        if self.claude_settings.exists():
            try:
                settings = json.loads(self.claude_settings.read_text())
                hooks_config = settings.get("hooks", {})

                for event, matchers in hooks_config.items():
                    for matcher_config in matchers:
                        matcher = matcher_config.get("matcher", "*")
                        for hook in matcher_config.get("hooks", []):
                            hooks.append(HookInfo(
                                event=event,
                                matcher=matcher,
                                hook_type=hook.get("type", "command"),
                                command=hook.get("command", hook.get("prompt", "")),
                                timeout=hook.get("timeout", 60),
                                source_path=self.claude_settings,
                                source_platform="claude"
                            ))
            except Exception as e:
                self.log(f"Failed to load hooks from settings: {e}", "error")

        if self.claude_hooks.exists():
            for hook_file in self.claude_hooks.glob("*.sh"):
                hooks.append(HookInfo(
                    event="PreToolUse",
                    matcher="*",
                    hook_type="command",
                    command=str(hook_file),
                    source_path=hook_file,
                    source_platform="claude"
                ))
        return hooks

    def load_claude_plugins(self) -> list[PluginInfo]:
        """Load all Claude Code plugins."""
        plugins = []
        if not self.claude_plugins.exists():
            return plugins

        for plugin_dir in self.claude_plugins.iterdir():
            if not plugin_dir.is_dir():
                continue
            plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
            if not plugin_json.exists():
                continue

            try:
                manifest = json.loads(plugin_json.read_text())
                author = manifest.get("author", {})
                author_name = author.get("name", "") if isinstance(author, dict) else str(author)

                plugins.append(PluginInfo(
                    name=manifest.get("name", plugin_dir.name),
                    description=manifest.get("description", ""),
                    version=manifest.get("version", "1.0.0"),
                    author=author_name,
                    source_path=plugin_dir,
                    has_commands=(plugin_dir / "commands").exists(),
                    has_agents=(plugin_dir / "agents").exists(),
                    has_skills=(plugin_dir / "skills").exists(),
                    has_hooks=(plugin_dir / "hooks").exists(),
                    has_mcp=(plugin_dir / ".mcp.json").exists(),
                    source_platform="claude"
                ))
            except Exception as e:
                self.log(f"Failed to load plugin {plugin_dir}: {e}", "error")
        return plugins

    def load_claude_mcp(self) -> dict:
        """Load MCP server configurations from Claude Code."""
        mcp_config = {}
        if self.claude_mcp.exists():
            try:
                config = json.loads(self.claude_mcp.read_text())
                mcp_config.update(config.get("mcpServers", config))
            except Exception as e:
                self.log(f"Failed to load .mcp.json: {e}", "error")

        if self.claude_plugins.exists():
            for plugin_dir in self.claude_plugins.iterdir():
                if not plugin_dir.is_dir():
                    continue
                plugin_mcp = plugin_dir / ".mcp.json"
                if plugin_mcp.exists():
                    try:
                        config = json.loads(plugin_mcp.read_text())
                        servers = config.get("mcpServers", config)
                        for name, cfg in servers.items():
                            mcp_config[f"{plugin_dir.name}_{name}"] = cfg
                    except Exception:
                        pass
        return mcp_config

    def load_all_claude(self):
        """Load all components from Claude Code."""
        self.agents = self.load_claude_agents()
        self.skills = self.load_claude_skills()
        self.commands = self.load_claude_commands()
        self.hooks = self.load_claude_hooks()
        self.plugins = self.load_claude_plugins()
        self.mcp_config = self.load_claude_mcp()

        self.log(f"Loaded from Claude Code: {len(self.agents)} agents, {len(self.skills)} skills, "
                f"{len(self.commands)} commands, {len(self.hooks)} hooks, {len(self.plugins)} plugins, "
                f"{len(self.mcp_config)} MCP servers")

    # =========================================================================
    # Core Sync Methods
    # =========================================================================

    def _sync_skills_to_directory(self, target_dir: Path, platform_name: str, with_frontmatter: bool = True):
        """Sync skills to a target directory."""
        if not self.dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for skill in self.skills:
            if skill.source_platform != "claude":
                continue

            target_skill_dir = target_dir / skill.name
            if self.dry_run:
                self.log(f"Would copy skill: {skill.name} -> {target_skill_dir}", "dry")
            else:
                if target_skill_dir.exists():
                    shutil.rmtree(target_skill_dir)
                shutil.copytree(skill.source_path, target_skill_dir)

                # If platform doesn't support frontmatter, strip it
                if not with_frontmatter:
                    skill_md = target_skill_dir / "SKILL.md"
                    if skill_md.exists():
                        content = skill_md.read_text()
                        skill_md.write_text(strip_yaml_frontmatter(content))

                self.log(f"Copied skill ({platform_name}): {skill.name}", "success")

        # Convert agents to skills
        agents_as_skills = target_dir / "_claude_agents"
        if not self.dry_run:
            agents_as_skills.mkdir(parents=True, exist_ok=True)

        for agent in self.agents:
            if agent.source_platform != "claude":
                continue

            agent_skill_dir = agents_as_skills / agent.name
            if self.dry_run:
                self.log(f"Would create agent-skill: {agent.name}", "dry")
            else:
                agent_skill_dir.mkdir(parents=True, exist_ok=True)
                desc = agent.description
                if isinstance(desc, list):
                    desc = " ".join(desc)
                desc = str(desc).replace('"', '\\"').replace('\n', ' ')[:200]

                if with_frontmatter:
                    skill_content = f"""---
name: {agent.name}
description: "{desc}"
---

{agent.content}
"""
                else:
                    skill_content = f"""# {agent.name}

{desc}

{agent.content}
"""
                (agent_skill_dir / "SKILL.md").write_text(skill_content)
                self.log(f"Created agent-skill ({platform_name}): {agent.name}", "success")

    def _sync_commands_as_files(self, target_dir: Path, platform_name: str, extension: str = ".md"):
        """Sync commands as individual files (for Cursor, Roo Code, etc.)."""
        if not self.commands:
            return

        if not self.dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

        for cmd in self.commands:
            if cmd.source_platform != "claude":
                continue

            filename = f"{cmd.name}{extension}"
            target_file = target_dir / filename

            # Strip frontmatter for plain MD platforms
            content = f"""# {cmd.name}

{cmd.description}

{cmd.content}
"""
            if self.dry_run:
                self.log(f"Would create command: {filename}", "dry")
            else:
                target_file.write_text(content)
                self.log(f"Created command ({platform_name}): {cmd.name}", "success")

    def _sync_hooks_to_json(self, target_file: Path, platform_name: str):
        """Sync hooks to a hooks.json file."""
        if not self.hooks:
            return

        hooks_data = {"hooks": {}}
        for hook in self.hooks:
            if hook.source_platform != "claude":
                continue

            if hook.event not in hooks_data["hooks"]:
                hooks_data["hooks"][hook.event] = []

            matcher_found = False
            for matcher_config in hooks_data["hooks"][hook.event]:
                if matcher_config.get("matcher") == hook.matcher:
                    matcher_config["hooks"].append({
                        "type": hook.hook_type,
                        "command": hook.command,
                        "timeout": hook.timeout
                    })
                    matcher_found = True
                    break

            if not matcher_found:
                hooks_data["hooks"][hook.event].append({
                    "matcher": hook.matcher,
                    "hooks": [{
                        "type": hook.hook_type,
                        "command": hook.command,
                        "timeout": hook.timeout
                    }]
                })

        if self.dry_run:
            self.log(f"Would write hooks.json ({platform_name})", "dry")
        else:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(json.dumps(hooks_data, indent=2))
            self.log(f"Synced {len(self.hooks)} hooks ({platform_name})", "success")

    def _sync_mcp_to_json(self, target_file: Path, platform_name: str, use_extension_path: bool = False):
        """Sync MCP configuration to a JSON file."""
        if not self.mcp_config:
            return

        if use_extension_path:
            mcp_data = {"mcpServers": transform_mcp_paths_to_gemini(self.mcp_config, self.claude_dir)}
        else:
            mcp_data = {"mcpServers": self.mcp_config}

        if self.dry_run:
            self.log(f"Would write MCP config ({platform_name})", "dry")
        else:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(json.dumps(mcp_data, indent=2))
            self.log(f"Synced {len(self.mcp_config)} MCP servers ({platform_name})", "success")

    # =========================================================================
    # Platform-Specific Sync Methods
    # =========================================================================

    def sync_to_gemini(self):
        """Sync to Gemini CLI and Antigravity."""
        self.log("Syncing to Gemini CLI...", "platform")

        # Sync skills
        self._sync_skills_to_directory(self.gemini_skills, "Gemini CLI", with_frontmatter=True)

        # Create claude-sync extension
        claude_ext_dir = self.gemini_extensions / "claude-sync"
        if not self.dry_run:
            claude_ext_dir.mkdir(parents=True, exist_ok=True)

            # Extension manifest
            ext_manifest = {
                "name": "claude-sync",
                "version": "1.0.0",
                "description": f"Auto-synced from Claude Code on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "contextFileName": "GEMINI.md"
            }

            if self.mcp_config:
                ext_manifest["mcpServers"] = transform_mcp_paths_to_gemini(self.mcp_config, self.claude_dir)
                all_env = {}
                for server_cfg in self.mcp_config.values():
                    if "env" in server_cfg:
                        all_env.update(server_cfg["env"])
                if all_env:
                    ext_manifest["settings"] = infer_settings_from_env(all_env)

            (claude_ext_dir / "gemini-extension.json").write_text(json.dumps(ext_manifest, indent=2))

        # Sync hooks
        self._sync_hooks_to_json(claude_ext_dir / "hooks" / "hooks.json", "Gemini")

        # Sync commands as TOML
        if self.commands and not self.dry_run:
            commands_dir = claude_ext_dir / "commands"
            commands_dir.mkdir(parents=True, exist_ok=True)
            for cmd in self.commands:
                toml_content = f'''[command]
description = "{cmd.description}"
argument_hint = "{cmd.argument_hint}"

[prompt]
content = """
{cmd.content}
"""
'''
                (commands_dir / f"{cmd.name}.toml").write_text(toml_content)
            self.log(f"Synced {len(self.commands)} commands (Gemini)", "success")

        # Generate GEMINI.md
        self._generate_context_md(self.gemini_md, "GEMINI.md")

        # Sync to Antigravity (same format)
        self.log("Syncing to Antigravity...", "platform")
        self._sync_skills_to_directory(self.antigravity_skills, "Antigravity", with_frontmatter=True)

    def sync_to_codex(self):
        """Sync to Codex CLI."""
        self.log("Syncing to Codex CLI...", "platform")

        if not self.dry_run:
            self.codex_dir.mkdir(parents=True, exist_ok=True)

        # Sync skills (same format as Claude)
        self._sync_skills_to_directory(self.codex_skills, "Codex CLI", with_frontmatter=True)

        # Generate AGENTS.md
        self._generate_agents_md(self.codex_agents_md)

        # Generate config.toml.suggested
        self._generate_codex_config()

    def sync_to_opencode(self):
        """Sync to OpenCode."""
        self.log("Syncing to OpenCode...", "platform")

        if not self.dry_run:
            self.opencode_dir.mkdir(parents=True, exist_ok=True)

        # Skills are same format as Claude
        self._sync_skills_to_directory(self.opencode_skills, "OpenCode", with_frontmatter=True)

    def sync_to_trae(self):
        """Sync to Trae (ByteDance)."""
        self.log("Syncing to Trae...", "platform")

        if not self.dry_run:
            self.trae_dir.mkdir(parents=True, exist_ok=True)

        # Skills are same format as Claude
        self._sync_skills_to_directory(self.trae_skills, "Trae", with_frontmatter=True)

    def sync_to_continue(self):
        """Sync to Continue.dev."""
        self.log("Syncing to Continue...", "platform")

        if not self.dry_run:
            self.continue_dir.mkdir(parents=True, exist_ok=True)

        # Skills are same format as Claude
        self._sync_skills_to_directory(self.continue_skills, "Continue", with_frontmatter=True)

        # Sync MCP servers (Continue uses directory-based config)
        if self.mcp_config and not self.dry_run:
            self.continue_mcp.mkdir(parents=True, exist_ok=True)
            for name, config in self.mcp_config.items():
                mcp_file = self.continue_mcp / f"{name}.json"
                mcp_file.write_text(json.dumps(config, indent=2))
            self.log(f"Synced {len(self.mcp_config)} MCP servers (Continue)", "success")

    def sync_to_cursor(self):
        """Sync to Cursor."""
        self.log("Syncing to Cursor...", "platform")

        if not self.dry_run:
            self.cursor_dir.mkdir(parents=True, exist_ok=True)

        # Sync commands (plain MD, no frontmatter)
        self._sync_commands_as_files(self.cursor_commands, "Cursor", extension=".md")

        # Sync skills as rules (strip frontmatter)
        if self.skills or self.agents:
            rules_dir = self.cursor_rules
            if not self.dry_run:
                rules_dir.mkdir(parents=True, exist_ok=True)

            for skill in self.skills:
                if skill.source_platform != "claude":
                    continue
                skill_md = skill.source_path / "SKILL.md"
                if skill_md.exists():
                    content = strip_yaml_frontmatter(skill_md.read_text())
                    target = rules_dir / f"{skill.name}.md"
                    if not self.dry_run:
                        target.write_text(f"# {skill.name}\n\n{content}")
                        self.log(f"Created rule (Cursor): {skill.name}", "success")

            for agent in self.agents:
                if agent.source_platform != "claude":
                    continue
                target = rules_dir / f"{agent.name}.md"
                if not self.dry_run:
                    target.write_text(f"# {agent.name}\n\n{agent.description}\n\n{agent.content}")
                    self.log(f"Created rule (Cursor): {agent.name}", "success")

        # Sync MCP
        self._sync_mcp_to_json(self.cursor_mcp, "Cursor", use_extension_path=False)

    def sync_to_windsurf(self):
        """Sync to Windsurf."""
        self.log("Syncing to Windsurf...", "platform")

        if not self.dry_run:
            self.windsurf_dir.mkdir(parents=True, exist_ok=True)

        # Sync as workflows (plain MD)
        if not self.dry_run:
            self.windsurf_workflows.mkdir(parents=True, exist_ok=True)

        for skill in self.skills:
            if skill.source_platform != "claude":
                continue
            skill_md = skill.source_path / "SKILL.md"
            if skill_md.exists():
                content = strip_yaml_frontmatter(skill_md.read_text())
                target = self.windsurf_workflows / f"{skill.name}.md"
                if self.dry_run:
                    self.log(f"Would create workflow: {skill.name}", "dry")
                else:
                    target.write_text(f"# {skill.name}\n\n{skill.description}\n\n{content}")
                    self.log(f"Created workflow (Windsurf): {skill.name}", "success")

        for agent in self.agents:
            if agent.source_platform != "claude":
                continue
            target = self.windsurf_workflows / f"{agent.name}.md"
            if self.dry_run:
                self.log(f"Would create workflow: {agent.name}", "dry")
            else:
                target.write_text(f"# {agent.name}\n\n{agent.description}\n\n{agent.content}")
                self.log(f"Created workflow (Windsurf): {agent.name}", "success")

    def sync_to_roocode(self):
        """Sync to Roo Code."""
        self.log("Syncing to Roo Code...", "platform")

        if not self.dry_run:
            self.roo_dir.mkdir(parents=True, exist_ok=True)

        # Sync commands
        self._sync_commands_as_files(self.roo_commands, "Roo Code", extension=".md")

        # Sync skills as rules
        if not self.dry_run:
            self.roo_rules.mkdir(parents=True, exist_ok=True)

        for skill in self.skills:
            if skill.source_platform != "claude":
                continue
            skill_md = skill.source_path / "SKILL.md"
            if skill_md.exists():
                content = strip_yaml_frontmatter(skill_md.read_text())
                target = self.roo_rules / f"{skill.name}.md"
                if self.dry_run:
                    self.log(f"Would create rule: {skill.name}", "dry")
                else:
                    target.write_text(f"# {skill.name}\n\n{content}")
                    self.log(f"Created rule (Roo Code): {skill.name}", "success")

        for agent in self.agents:
            if agent.source_platform != "claude":
                continue
            target = self.roo_rules / f"{agent.name}.md"
            if self.dry_run:
                self.log(f"Would create rule: {agent.name}", "dry")
            else:
                target.write_text(f"# {agent.name}\n\n{agent.description}\n\n{agent.content}")
                self.log(f"Created rule (Roo Code): {agent.name}", "success")

    def sync_to_kiro(self):
        """Sync to Kiro (AWS)."""
        self.log("Syncing to Kiro...", "platform")

        if not self.dry_run:
            self.kiro_dir.mkdir(parents=True, exist_ok=True)
            self.kiro_steering.mkdir(parents=True, exist_ok=True)
            self.kiro_settings.mkdir(parents=True, exist_ok=True)

        # Sync skills/agents as steering files
        for skill in self.skills:
            if skill.source_platform != "claude":
                continue
            skill_md = skill.source_path / "SKILL.md"
            if skill_md.exists():
                content = strip_yaml_frontmatter(skill_md.read_text())
                target = self.kiro_steering / f"{skill.name}.md"
                if self.dry_run:
                    self.log(f"Would create steering: {skill.name}", "dry")
                else:
                    target.write_text(f"# {skill.name}\n\n{content}")
                    self.log(f"Created steering (Kiro): {skill.name}", "success")

        for agent in self.agents:
            if agent.source_platform != "claude":
                continue
            target = self.kiro_steering / f"{agent.name}.md"
            if self.dry_run:
                self.log(f"Would create steering: {agent.name}", "dry")
            else:
                target.write_text(f"# {agent.name}\n\n{agent.description}\n\n{agent.content}")
                self.log(f"Created steering (Kiro): {agent.name}", "success")

        # Generate AGENTS.md for Kiro (supports AGENTS.md standard)
        agents_md = self.kiro_steering / "AGENTS.md"
        self._generate_agents_md(agents_md)

        # Sync MCP
        self._sync_mcp_to_json(self.kiro_mcp, "Kiro", use_extension_path=False)

    def sync_to_copilot(self):
        """Sync to GitHub Copilot."""
        self.log("Syncing to GitHub Copilot...", "platform")

        if not self.dry_run:
            self.copilot_dir.mkdir(parents=True, exist_ok=True)
            self.copilot_prompts.mkdir(parents=True, exist_ok=True)

        # Sync skills as prompts
        for skill in self.skills:
            if skill.source_platform != "claude":
                continue
            skill_md = skill.source_path / "SKILL.md"
            if skill_md.exists():
                content = strip_yaml_frontmatter(skill_md.read_text())
                target = self.copilot_prompts / f"{skill.name}.prompt.md"
                if self.dry_run:
                    self.log(f"Would create prompt: {skill.name}", "dry")
                else:
                    target.write_text(f"# {skill.name}\n\n{skill.description}\n\n{content}")
                    self.log(f"Created prompt (Copilot): {skill.name}", "success")

        for agent in self.agents:
            if agent.source_platform != "claude":
                continue
            target = self.copilot_prompts / f"{agent.name}.prompt.md"
            if self.dry_run:
                self.log(f"Would create prompt: {agent.name}", "dry")
            else:
                target.write_text(f"# {agent.name}\n\n{agent.description}\n\n{agent.content}")
                self.log(f"Created prompt (Copilot): {agent.name}", "success")

        # Generate copilot-instructions.md
        if self.claude_md.exists() and not self.dry_run:
            content = self.claude_md.read_text()
            self.copilot_instructions.write_text(f"""# GitHub Copilot Custom Instructions
> Auto-generated from Claude Code CLAUDE.md

{content}
""")
            self.log("Generated copilot-instructions.md", "success")

    def sync_to_aider(self):
        """Sync to Aider (generates CONVENTIONS.md)."""
        self.log("Syncing to Aider...", "platform")

        # Generate aggregated CONVENTIONS.md
        sections = [f"""# Coding Conventions
> Auto-generated from Claude Code on {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""]

        if self.claude_md.exists():
            sections.append("## Global Instructions\n\n")
            sections.append(self.claude_md.read_text())
            sections.append("\n\n---\n\n")

        if self.skills:
            sections.append("## Skills & Guidelines\n\n")
            for skill in self.skills:
                skill_md = skill.source_path / "SKILL.md"
                if skill_md.exists():
                    content = strip_yaml_frontmatter(skill_md.read_text())
                    sections.append(f"### {skill.name}\n\n{skill.description}\n\n{content[:500]}...\n\n")

        if self.agents:
            sections.append("## Agent Modes\n\n")
            for agent in self.agents:
                sections.append(f"### {agent.name}\n\n{agent.description}\n\n")

        conventions_content = "".join(sections)

        if self.dry_run:
            self.log(f"Would write CONVENTIONS.md ({len(conventions_content)} chars)", "dry")
        else:
            self.aider_conventions.write_text(conventions_content)
            self.log("Generated CONVENTIONS.md (Aider)", "success")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _generate_context_md(self, target_path: Path, filename: str):
        """Generate a context file (GEMINI.md, etc.)."""
        sections = [f"""# {filename.replace('.md', '')} Configuration
> Auto-generated from Claude Code on {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""]

        if self.claude_md.exists():
            sections.append("## Global Instructions\n\n")
            sections.append(self.claude_md.read_text())
            sections.append("\n\n")

        if self.agents:
            sections.append("## Available Agents\n\n")
            for agent in self.agents:
                sections.append(f"- **{agent.name}**: {str(agent.description)[:100]}\n")
            sections.append("\n")

        if self.skills:
            sections.append("## Available Skills\n\n")
            for skill in self.skills:
                sections.append(f"- **{skill.name}**: {skill.description[:100]}\n")
            sections.append("\n")

        if self.commands:
            sections.append("## Available Commands\n\n")
            for cmd in self.commands:
                sections.append(f"- `/{cmd.name}`: {cmd.description}\n")

        content = "".join(sections)

        if self.dry_run:
            self.log(f"Would write {filename} ({len(content)} chars)", "dry")
        else:
            if target_path.exists():
                shutil.copy(target_path, target_path.with_suffix(".md.backup"))
            target_path.write_text(content)
            self.log(f"Generated {filename}", "success")

    def _generate_agents_md(self, target_path: Path):
        """Generate AGENTS.md for Codex/Kiro."""
        sections = [f"""# Agent Instructions
> Auto-generated from Claude Code on {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""]

        if self.claude_md.exists():
            sections.append("## Global Instructions\n\n")
            sections.append(self.claude_md.read_text())
            sections.append("\n\n---\n\n")

        if self.agents:
            sections.append("## Specialized Agents\n\n")
            for agent in sorted(self.agents, key=lambda a: a.name):
                sections.append(f"### {agent.name.replace('-', ' ').title()}\n\n")
                sections.append(f"**Purpose**: {agent.description}\n\n")
                sections.append(agent.content[:2000])
                sections.append("\n\n---\n\n")

        content = "".join(sections)

        if self.dry_run:
            self.log(f"Would write AGENTS.md ({len(content)} chars)", "dry")
        else:
            if target_path.exists():
                shutil.copy(target_path, target_path.with_suffix(".md.backup"))
            target_path.write_text(content)
            self.log(f"Generated AGENTS.md", "success")

    def _generate_codex_config(self):
        """Generate config.toml.suggested for Codex."""
        config = f"""# Codex CLI Configuration
# Auto-generated from Claude Code on {datetime.now().strftime('%Y-%m-%d %H:%M')}

model = "o4-mini"
approval_mode = "suggest"
project_doc_fallback_filenames = ["AGENTS.md", "CLAUDE.md"]

[features]
shell_snapshot = true
web_search_request = true
"""
        target = self.codex_dir / "config.toml.suggested"

        if self.dry_run:
            self.log("Would write config.toml.suggested", "dry")
        else:
            target.write_text(config)
            self.log("Generated config.toml.suggested", "success")

    # =========================================================================
    # Main Sync Operations
    # =========================================================================

    def sync_all(self):
        """Sync to all supported platforms."""
        self.load_all_claude()

        self.sync_to_gemini()      # Includes Antigravity
        self.sync_to_codex()
        self.sync_to_opencode()
        self.sync_to_trae()
        self.sync_to_continue()
        self.sync_to_cursor()
        self.sync_to_windsurf()
        self.sync_to_roocode()
        self.sync_to_kiro()
        self.sync_to_copilot()
        self.sync_to_aider()

        self.save_sync_state()
        self.log("Sync complete to all platforms!", "success")

    def sync_platform(self, platform: str):
        """Sync to a specific platform."""
        self.load_all_claude()

        sync_methods = {
            "gemini": self.sync_to_gemini,
            "antigravity": lambda: self._sync_skills_to_directory(self.antigravity_skills, "Antigravity", True),
            "codex": self.sync_to_codex,
            "opencode": self.sync_to_opencode,
            "trae": self.sync_to_trae,
            "continue": self.sync_to_continue,
            "cursor": self.sync_to_cursor,
            "windsurf": self.sync_to_windsurf,
            "roocode": self.sync_to_roocode,
            "kiro": self.sync_to_kiro,
            "copilot": self.sync_to_copilot,
            "aider": self.sync_to_aider,
        }

        if platform in sync_methods:
            sync_methods[platform]()
            self.save_sync_state()
        else:
            self.log(f"Unknown platform: {platform}", "error")

    def save_sync_state(self):
        """Save sync state for tracking."""
        state = {
            "last_sync": datetime.now().isoformat(),
            "agents_synced": [a.name for a in self.agents],
            "skills_synced": [s.name for s in self.skills],
            "commands_synced": [c.name for c in self.commands],
            "hooks_synced": len(self.hooks),
            "mcp_servers_synced": len(self.mcp_config),
            "plugins_synced": [p.name for p in self.plugins],
        }

        if not self.dry_run:
            self.sync_log_path.parent.mkdir(parents=True, exist_ok=True)
            self.sync_log_path.write_text(json.dumps(state, indent=2))

    # =========================================================================
    # Export/Import Bundle
    # =========================================================================

    def export_bundle(self, output_path: Optional[Path] = None, include_plugins: bool = True) -> Path:
        """
        Export all Claude Code components to a compressed bundle.

        Creates a .tar.gz archive containing:
        - agents/       All agent definitions
        - skills/       All skills with their subdirectories
        - commands/     All slash commands
        - hooks/        Hook scripts
        - plugins/      Plugin directories (optional)
        - settings.json Hook configuration
        - .mcp.json     MCP server configuration
        - CLAUDE.md     Global instructions
        - manifest.json Bundle metadata

        Args:
            output_path: Custom output path (default: claude-bundle-TIMESTAMP.tar.gz)
            include_plugins: Whether to include plugins (can be large)

        Returns:
            Path to the created bundle file
        """
        import tarfile
        import tempfile

        self.load_all_claude()

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if output_path is None:
            output_path = Path.cwd() / f"claude-bundle-{timestamp}.tar.gz"
        else:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = output_path / f"claude-bundle-{timestamp}.tar.gz"

        self.log(f"Creating bundle: {output_path}", "info")

        # Create manifest
        manifest = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "source": "claude-code",
            "components": {
                "agents": len(self.agents),
                "skills": len(self.skills),
                "commands": len(self.commands),
                "hooks": len(self.hooks),
                "plugins": len(self.plugins) if include_plugins else 0,
                "mcp_servers": len(self.mcp_config),
            },
            "agent_names": [a.name for a in self.agents],
            "skill_names": [s.name for s in self.skills],
            "plugin_names": [p.name for p in self.plugins] if include_plugins else [],
        }

        if self.dry_run:
            self.log("Would create bundle with:", "dry")
            for component, count in manifest["components"].items():
                self.log(f"  {component}: {count}", "dry")
            return output_path

        # Create temporary directory for staging
        with tempfile.TemporaryDirectory() as tmpdir:
            staging = Path(tmpdir) / "claude-bundle"
            staging.mkdir()

            # Copy agents
            if self.claude_agents.exists():
                agents_dest = staging / "agents"
                shutil.copytree(self.claude_agents, agents_dest)
                self.log(f"  Added {len(list(agents_dest.glob('*.md')))} agents", "info")

            # Copy skills
            if self.claude_skills.exists():
                skills_dest = staging / "skills"
                shutil.copytree(self.claude_skills, skills_dest)
                self.log(f"  Added {len(list(skills_dest.iterdir()))} skills", "info")

            # Copy commands
            if self.claude_commands.exists():
                commands_dest = staging / "commands"
                shutil.copytree(self.claude_commands, commands_dest)
                self.log(f"  Added {len(list(commands_dest.glob('*.md')))} commands", "info")

            # Copy hooks
            if self.claude_hooks.exists():
                hooks_dest = staging / "hooks"
                shutil.copytree(self.claude_hooks, hooks_dest)
                self.log(f"  Added hooks directory", "info")

            # Copy plugins (optional)
            if include_plugins and self.claude_plugins.exists():
                plugins_dest = staging / "plugins"
                shutil.copytree(self.claude_plugins, plugins_dest)
                self.log(f"  Added {len(list(plugins_dest.iterdir()))} plugins", "info")

            # Copy settings.json
            if self.claude_settings.exists():
                shutil.copy2(self.claude_settings, staging / "settings.json")
                self.log("  Added settings.json", "info")

            # Copy .mcp.json
            if self.claude_mcp.exists():
                shutil.copy2(self.claude_mcp, staging / ".mcp.json")
                self.log("  Added .mcp.json", "info")

            # Copy CLAUDE.md
            if self.claude_md.exists():
                shutil.copy2(self.claude_md, staging / "CLAUDE.md")
                self.log("  Added CLAUDE.md", "info")

            # Write manifest
            (staging / "manifest.json").write_text(json.dumps(manifest, indent=2))

            # Create tar.gz archive
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(staging, arcname="claude-bundle")

        # Calculate size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        self.log(f"Bundle created: {output_path} ({size_mb:.2f} MB)", "success")

        return output_path

    def import_bundle(self, bundle_path: Path, merge: bool = False, backup: bool = True) -> bool:
        """
        Import Claude Code components from a compressed bundle.

        Args:
            bundle_path: Path to the .tar.gz bundle file
            merge: If True, merge with existing; if False, replace
            backup: If True, backup existing config before import

        Returns:
            True if import successful, False otherwise
        """
        import tarfile
        import tempfile

        bundle_path = Path(bundle_path)
        if not bundle_path.exists():
            self.log(f"Bundle not found: {bundle_path}", "error")
            return False

        if not bundle_path.suffix == ".gz" and not str(bundle_path).endswith(".tar.gz"):
            self.log("Bundle must be a .tar.gz file", "error")
            return False

        self.log(f"Importing bundle: {bundle_path}", "info")

        # Extract to temp directory first to validate
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with tarfile.open(bundle_path, "r:gz") as tar:
                    tar.extractall(tmpdir)
            except tarfile.TarError as e:
                self.log(f"Failed to extract bundle: {e}", "error")
                return False

            # Find the bundle directory
            extracted = Path(tmpdir)
            bundle_dir = extracted / "claude-bundle"
            if not bundle_dir.exists():
                # Try to find it
                for item in extracted.iterdir():
                    if item.is_dir():
                        bundle_dir = item
                        break

            # Read manifest
            manifest_path = bundle_dir / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                self.log(f"Bundle version: {manifest.get('version', 'unknown')}", "info")
                self.log(f"Created: {manifest.get('created', 'unknown')}", "info")
                components = manifest.get("components", {})
                for comp, count in components.items():
                    self.log(f"  {comp}: {count}", "info")
            else:
                self.log("No manifest found, proceeding anyway", "warning")

            if self.dry_run:
                self.log("Would import the above components", "dry")
                if not merge:
                    self.log("Would REPLACE existing configuration", "dry")
                else:
                    self.log("Would MERGE with existing configuration", "dry")
                return True

            # Backup existing config if requested
            if backup and self.claude_dir.exists():
                backup_path = self._create_backup()
                if backup_path:
                    self.log(f"Backup created: {backup_path}", "info")

            # Ensure claude directory exists
            self.claude_dir.mkdir(parents=True, exist_ok=True)

            # Import each component
            components_imported = []

            # Agents
            src_agents = bundle_dir / "agents"
            if src_agents.exists():
                if not merge and self.claude_agents.exists():
                    shutil.rmtree(self.claude_agents)
                self.claude_agents.mkdir(parents=True, exist_ok=True)
                for agent_file in src_agents.glob("*.md"):
                    dest = self.claude_agents / agent_file.name
                    if merge and dest.exists():
                        self.log(f"  Skipping existing agent: {agent_file.stem}", "info")
                    else:
                        shutil.copy2(agent_file, dest)
                        components_imported.append(f"agent:{agent_file.stem}")

            # Skills
            src_skills = bundle_dir / "skills"
            if src_skills.exists():
                if not merge and self.claude_skills.exists():
                    shutil.rmtree(self.claude_skills)
                self.claude_skills.mkdir(parents=True, exist_ok=True)
                for skill_dir in src_skills.iterdir():
                    if skill_dir.is_dir():
                        dest = self.claude_skills / skill_dir.name
                        if merge and dest.exists():
                            self.log(f"  Skipping existing skill: {skill_dir.name}", "info")
                        else:
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(skill_dir, dest)
                            components_imported.append(f"skill:{skill_dir.name}")

            # Commands
            src_commands = bundle_dir / "commands"
            if src_commands.exists():
                if not merge and self.claude_commands.exists():
                    shutil.rmtree(self.claude_commands)
                self.claude_commands.mkdir(parents=True, exist_ok=True)
                for cmd_file in src_commands.glob("*.md"):
                    dest = self.claude_commands / cmd_file.name
                    if merge and dest.exists():
                        self.log(f"  Skipping existing command: {cmd_file.stem}", "info")
                    else:
                        shutil.copy2(cmd_file, dest)
                        components_imported.append(f"command:{cmd_file.stem}")

            # Hooks
            src_hooks = bundle_dir / "hooks"
            if src_hooks.exists():
                if not merge and self.claude_hooks.exists():
                    shutil.rmtree(self.claude_hooks)
                self.claude_hooks.mkdir(parents=True, exist_ok=True)
                for hook_file in src_hooks.iterdir():
                    dest = self.claude_hooks / hook_file.name
                    if merge and dest.exists():
                        self.log(f"  Skipping existing hook: {hook_file.name}", "info")
                    else:
                        if hook_file.is_dir():
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(hook_file, dest)
                        else:
                            shutil.copy2(hook_file, dest)
                        components_imported.append(f"hook:{hook_file.name}")

            # Plugins
            src_plugins = bundle_dir / "plugins"
            if src_plugins.exists():
                if not merge and self.claude_plugins.exists():
                    shutil.rmtree(self.claude_plugins)
                self.claude_plugins.mkdir(parents=True, exist_ok=True)
                for plugin_dir in src_plugins.iterdir():
                    if plugin_dir.is_dir():
                        dest = self.claude_plugins / plugin_dir.name
                        if merge and dest.exists():
                            self.log(f"  Skipping existing plugin: {plugin_dir.name}", "info")
                        else:
                            if dest.exists():
                                shutil.rmtree(dest)
                            shutil.copytree(plugin_dir, dest)
                            components_imported.append(f"plugin:{plugin_dir.name}")

            # Settings
            src_settings = bundle_dir / "settings.json"
            if src_settings.exists():
                if merge and self.claude_settings.exists():
                    # Merge settings
                    existing = json.loads(self.claude_settings.read_text())
                    incoming = json.loads(src_settings.read_text())
                    # Deep merge hooks array
                    if "hooks" in incoming:
                        existing_hooks = existing.get("hooks", [])
                        for hook in incoming["hooks"]:
                            if hook not in existing_hooks:
                                existing_hooks.append(hook)
                        existing["hooks"] = existing_hooks
                    self.claude_settings.write_text(json.dumps(existing, indent=2))
                else:
                    shutil.copy2(src_settings, self.claude_settings)
                components_imported.append("settings.json")

            # MCP config
            src_mcp = bundle_dir / ".mcp.json"
            if src_mcp.exists():
                if merge and self.claude_mcp.exists():
                    # Merge MCP configs
                    existing = json.loads(self.claude_mcp.read_text())
                    incoming = json.loads(src_mcp.read_text())
                    existing.update(incoming)
                    self.claude_mcp.write_text(json.dumps(existing, indent=2))
                else:
                    shutil.copy2(src_mcp, self.claude_mcp)
                components_imported.append(".mcp.json")

            # CLAUDE.md
            src_claude_md = bundle_dir / "CLAUDE.md"
            if src_claude_md.exists():
                if merge and self.claude_md.exists():
                    self.log("  Skipping CLAUDE.md (merge mode)", "info")
                else:
                    shutil.copy2(src_claude_md, self.claude_md)
                    components_imported.append("CLAUDE.md")

        self.log(f"Imported {len(components_imported)} components", "success")
        return True

    def _create_backup(self) -> Optional[Path]:
        """Create a backup of existing Claude config."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.home / f".claude-backup-{timestamp}.tar.gz"

        try:
            return self.export_bundle(backup_path, include_plugins=True)
        except Exception as e:
            self.log(f"Backup failed: {e}", "warning")
            return None

    def list_components(self):
        """List all components that would be synced (no emojis)."""
        self.load_all_claude()

        print("\n" + "=" * 60)
        print("  CLAUDE CODE COMPONENTS")
        print("=" * 60)

        print(f"\n  Agents ({len(self.agents)}):")
        for agent in sorted(self.agents, key=lambda a: a.name):
            desc = str(agent.description)[:50] if agent.description else ""
            print(f"   * {agent.name}: {desc}...")

        print(f"\n  Skills ({len(self.skills)}):")
        for skill in sorted(self.skills, key=lambda s: s.name):
            extras = []
            if skill.has_scripts: extras.append("scripts")
            if skill.has_references: extras.append("refs")
            if skill.has_assets: extras.append("assets")
            extra_str = f" [{', '.join(extras)}]" if extras else ""
            print(f"   * {skill.name}{extra_str}")

        print(f"\n  Commands ({len(self.commands)}):")
        for cmd in sorted(self.commands, key=lambda c: c.name):
            desc = cmd.description[:40] if cmd.description else ""
            print(f"   * /{cmd.name}: {desc}...")

        print(f"\n  Hooks ({len(self.hooks)}):")
        for hook in self.hooks[:5]:
            print(f"   * {hook.event}[{hook.matcher}]")
        if len(self.hooks) > 5:
            print(f"   ... and {len(self.hooks) - 5} more")

        print(f"\n  Plugins ({len(self.plugins)}):")
        for plugin in sorted(self.plugins, key=lambda p: p.name):
            print(f"   * {plugin.name} v{plugin.version}")

        print(f"\n  MCP Servers ({len(self.mcp_config)}):")
        for name in list(self.mcp_config.keys())[:5]:
            print(f"   * {name}")
        if len(self.mcp_config) > 5:
            print(f"   ... and {len(self.mcp_config) - 5} more")

        print("\n" + "=" * 60)
        print("  TARGET PLATFORMS")
        print("=" * 60)
        print("""
   [+] Gemini CLI      ~/.gemini/skills/
   [+] Antigravity     ~/.gemini/antigravity/skills/
   [+] Codex CLI       ~/.codex/skills/
   [+] OpenCode        ~/.opencode/skills/
   [+] Trae            ~/.trae/skills/
   [+] Continue        ~/.continue/skills/
   [+] Cursor          ~/.cursor/commands/, ~/.cursor/rules/
   [+] Windsurf        ~/.windsurf/workflows/
   [+] Roo Code        ~/.roo/commands/, ~/.roo/rules/
   [+] Kiro            ~/.kiro/steering/
   [+] GitHub Copilot  ~/.github/prompts/
   [+] Aider           ./CONVENTIONS.md
""")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Agent Management & Sync Suite - Manage and sync Claude Code agents across platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  No arguments           Launch interactive menu (recommended)
  --all / -a             Sync to all platforms
  --platform / -p        Sync to specific platform
  --list / -l            List all syncable components
  --export / -e          Export config to portable bundle
  --import FILE          Import config from bundle

Supported Platforms:
  gemini, antigravity, codex, opencode, trae, continue,
  cursor, windsurf, roocode, kiro, copilot, aider

Examples:
  %(prog)s                          Launch interactive menu
  %(prog)s --all                    Sync to all platforms
  %(prog)s --platform gemini        Sync only to Gemini CLI
  %(prog)s --list                   List all syncable components
  %(prog)s --dry-run --all          Preview sync without changes
  %(prog)s --export                 Export to claude-bundle-TIMESTAMP.tar.gz
  %(prog)s --export my-config.tar.gz   Export to specific file
  %(prog)s --import bundle.tar.gz  Import from bundle (replaces config)
  %(prog)s --import bundle.tar.gz --merge  Import and merge with existing
        """
    )

    parser.add_argument("--all", "-a", action="store_true", help="Sync to all platforms")
    parser.add_argument("--platform", "-p", choices=list(PLATFORMS.keys()), help="Sync to specific platform")
    parser.add_argument("--list", "-l", action="store_true", help="List components")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Preview changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive mode")
    parser.add_argument("--export", "-e", nargs="?", const=True, metavar="FILE",
                        help="Export all config to compressed bundle")
    parser.add_argument("--import", dest="import_file", metavar="FILE",
                        help="Import config from compressed bundle")
    parser.add_argument("--merge", action="store_true",
                        help="Merge imported config with existing (default: replace)")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip backup when importing (default: create backup)")
    parser.add_argument("--no-plugins", action="store_true",
                        help="Exclude plugins from export (smaller bundle)")

    args = parser.parse_args()
    syncer = AgentSync(dry_run=args.dry_run, verbose=args.verbose)

    # Determine mode
    if args.export:
        output_path = None if args.export is True else Path(args.export)
        syncer.export_bundle(output_path, include_plugins=not args.no_plugins)
    elif args.import_file:
        syncer.import_bundle(
            Path(args.import_file),
            merge=args.merge,
            backup=not args.no_backup
        )
    elif args.list:
        syncer.list_components()
    elif args.all:
        syncer.sync_all()
    elif args.platform:
        syncer.sync_platform(args.platform)
    elif args.interactive or not any([args.all, args.platform, args.list, args.export, args.import_file]):
        # Launch interactive menu when no arguments provided
        try:
            from menu.main_menu import MainMenu
            menu = MainMenu(syncer)
            menu.run()
        except ImportError:
            # Fallback if menu module not found
            print("Interactive menu not available. Use --help for options.")
            parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
