"""
Connection Monitor - Checks CLI tool availability and OAuth status for agentic coding platforms.
Detects installation, configuration health, and authentication state.
"""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class PlatformStatus:
    """Status of a single platform."""
    name: str
    cli_name: str
    installed: bool = False
    cli_available: bool = False
    cli_version: Optional[str] = None
    config_exists: bool = False
    config_path: Optional[Path] = None
    auth_status: str = "unknown"  # "authenticated", "unauthenticated", "unknown", "not_applicable"
    auth_method: Optional[str] = None  # "oauth", "api_key", "token", "none"
    auth_details: Optional[str] = None
    last_checked: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    fix_instructions: Optional[str] = None


@dataclass
class ConnectionStatus:
    """Overall connection status."""
    platforms: list[PlatformStatus] = field(default_factory=list)
    last_checked: str = field(default_factory=lambda: datetime.now().isoformat())
    healthy_count: int = 0
    warning_count: int = 0
    error_count: int = 0


class ConnectionMonitor:
    """
    Monitors connectivity and authentication status for agentic coding platforms.
    """

    # Platform definitions with CLI names and config paths
    PLATFORMS = {
        "claude": {
            "name": "Claude Code",
            "cli": "claude",
            "config_dir": ".claude",
            "auth_method": "oauth",
            "auth_files": [".credentials.json", "credentials.json"],
            "version_cmd": ["claude", "--version"],
        },
        "codex": {
            "name": "Codex CLI",
            "cli": "codex",
            "config_dir": ".codex",
            "auth_method": "api_key",
            "auth_files": ["config.json", ".env"],
            "env_vars": ["OPENAI_API_KEY"],
            "version_cmd": ["codex", "--version"],
        },
        "gemini": {
            "name": "Gemini CLI",
            "cli": "gemini",
            "config_dir": ".gemini",
            "auth_method": "oauth",
            "auth_files": ["credentials.json", ".credentials"],
            "version_cmd": ["gemini", "--version"],
        },
        "cursor": {
            "name": "Cursor",
            "cli": "cursor",
            "config_dir": ".cursor",
            "auth_method": "oauth",
            "auth_files": ["auth.json", "User/globalStorage/cursor.auth"],
            "version_cmd": ["cursor", "--version"],
        },
        "windsurf": {
            "name": "Windsurf",
            "cli": "windsurf",
            "config_dir": ".windsurf",
            "auth_method": "oauth",
            "auth_files": ["auth.json", ".auth"],
            "version_cmd": ["windsurf", "--version"],
        },
        "continue": {
            "name": "Continue",
            "cli": "continue",
            "config_dir": ".continue",
            "auth_method": "api_key",
            "auth_files": ["config.json"],
            "env_vars": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "version_cmd": None,
        },
        "aider": {
            "name": "Aider",
            "cli": "aider",
            "config_dir": ".aider",
            "auth_method": "api_key",
            "auth_files": [".aider.conf.yml", ".env"],
            "env_vars": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "version_cmd": ["aider", "--version"],
        },
        "copilot": {
            "name": "GitHub Copilot",
            "cli": "gh",
            "config_dir": ".config/gh",
            "auth_method": "oauth",
            "auth_files": ["hosts.yml"],
            "version_cmd": ["gh", "--version"],
            "auth_cmd": ["gh", "auth", "status"],
        },
        "roocode": {
            "name": "Roo Code",
            "cli": "roo",
            "config_dir": ".roo",
            "auth_method": "api_key",
            "auth_files": ["config.json", ".env"],
            "version_cmd": None,
        },
        "kiro": {
            "name": "Kiro",
            "cli": "kiro",
            "config_dir": ".kiro",
            "auth_method": "oauth",
            "auth_files": ["auth.json", "credentials.json"],
            "version_cmd": None,
        },
        "opencode": {
            "name": "OpenCode",
            "cli": "opencode",
            "config_dir": ".opencode",
            "auth_method": "api_key",
            "auth_files": ["config.json"],
            "env_vars": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
            "version_cmd": None,
        },
        "antigravity": {
            "name": "Antigravity",
            "cli": "ag",
            "config_dir": ".agent",
            "auth_method": "api_key",
            "auth_files": ["config.json", ".env"],
            "version_cmd": None,
        },
        "trae": {
            "name": "Trae",
            "cli": "trae",
            "config_dir": ".trae",
            "auth_method": "api_key",
            "auth_files": ["config.json"],
            "version_cmd": None,
        },
    }

    def __init__(self):
        self.home = Path.home()
        self._cache: dict[str, PlatformStatus] = {}
        self._cache_ttl = 60  # seconds

    def check_cli_available(self, cli_name: str) -> tuple[bool, Optional[str]]:
        """Check if a CLI tool is available in PATH."""
        path = shutil.which(cli_name)
        return (path is not None, path)

    def get_cli_version(self, version_cmd: list[str]) -> Optional[str]:
        """Get CLI version by running version command."""
        if not version_cmd:
            return None

        try:
            result = subprocess.run(
                version_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output
                output = result.stdout.strip() or result.stderr.strip()
                # Take first line, trim to reasonable length
                first_line = output.split('\n')[0]
                return first_line[:100] if first_line else None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        return None

    def check_auth_files(self, config_dir: Path, auth_files: list[str]) -> tuple[bool, Optional[Path]]:
        """Check if any authentication files exist."""
        for auth_file in auth_files:
            auth_path = config_dir / auth_file
            if auth_path.exists():
                return (True, auth_path)
        return (False, None)

    def check_env_vars(self, env_vars: list[str]) -> tuple[bool, Optional[str]]:
        """Check if any required environment variables are set."""
        for var in env_vars:
            if os.environ.get(var):
                return (True, var)
        return (False, None)

    def check_oauth_token_valid(self, auth_path: Path) -> tuple[bool, Optional[str]]:
        """Check if OAuth token exists and appears valid."""
        try:
            content = auth_path.read_text()
            data = json.loads(content)

            # Look for common token fields
            if any(key in data for key in ["access_token", "token", "oauth_token", "id_token"]):
                # Check for expiry if present
                if "expires_at" in data:
                    expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
                    if expires < datetime.now(expires.tzinfo):
                        return (False, "Token expired")
                return (True, "Token found")

            # For hosts.yml (GitHub CLI)
            if "github.com" in data:
                if data["github.com"].get("oauth_token"):
                    return (True, "GitHub OAuth token found")

        except (json.JSONDecodeError, KeyError, ValueError):
            # Try YAML for gh config
            try:
                import yaml
                content = auth_path.read_text()
                data = yaml.safe_load(content)
                if isinstance(data, dict) and "github.com" in data:
                    if data["github.com"].get("oauth_token"):
                        return (True, "GitHub OAuth token found")
            except Exception:
                pass

        return (False, None)

    def run_auth_check_cmd(self, auth_cmd: list[str]) -> tuple[bool, Optional[str]]:
        """Run an auth check command (like gh auth status)."""
        try:
            result = subprocess.run(
                auth_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return (True, result.stdout.strip()[:200])
            else:
                return (False, result.stderr.strip()[:200])
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        return (False, None)

    def check_platform(self, platform_id: str) -> PlatformStatus:
        """Check status of a single platform."""
        if platform_id not in self.PLATFORMS:
            return PlatformStatus(
                name=platform_id,
                cli_name=platform_id,
                error=f"Unknown platform: {platform_id}"
            )

        config = self.PLATFORMS[platform_id]
        status = PlatformStatus(
            name=config["name"],
            cli_name=config["cli"],
            auth_method=config.get("auth_method"),
        )

        # Check config directory
        config_dir = self.home / config["config_dir"]
        status.config_path = config_dir
        status.config_exists = config_dir.exists()
        status.installed = status.config_exists

        # Check CLI availability
        cli_available, cli_path = self.check_cli_available(config["cli"])
        status.cli_available = cli_available

        # Get CLI version
        if cli_available and config.get("version_cmd"):
            status.cli_version = self.get_cli_version(config["version_cmd"])

        # Check authentication
        auth_method = config.get("auth_method", "unknown")

        if auth_method == "oauth":
            # Check for OAuth auth files
            if status.config_exists:
                has_auth, auth_path = self.check_auth_files(
                    config_dir, config.get("auth_files", [])
                )
                if has_auth:
                    # Validate token
                    is_valid, detail = self.check_oauth_token_valid(auth_path)
                    if is_valid:
                        status.auth_status = "authenticated"
                        status.auth_details = detail
                    else:
                        status.auth_status = "unauthenticated"
                        status.auth_details = detail or "Token invalid or expired"
                        status.fix_instructions = f"Run `{config['cli']} login` or `{config['cli']} auth login` to re-authenticate"
                else:
                    status.auth_status = "unauthenticated"
                    status.auth_details = "No OAuth credentials found"
                    status.fix_instructions = f"Run `{config['cli']} login` to authenticate via OAuth"
            else:
                status.auth_status = "unauthenticated"
                status.auth_details = "Platform not configured"
                status.fix_instructions = f"Run `{config['cli']}` to set up the platform"

            # Special handling for GitHub CLI
            if config.get("auth_cmd"):
                is_auth, detail = self.run_auth_check_cmd(config["auth_cmd"])
                if is_auth:
                    status.auth_status = "authenticated"
                    status.auth_details = detail

        elif auth_method == "api_key":
            # Check environment variables first
            env_vars = config.get("env_vars", [])
            has_env, env_var = self.check_env_vars(env_vars)
            if has_env:
                status.auth_status = "authenticated"
                status.auth_details = f"API key set via {env_var}"
            elif status.config_exists:
                # Check config files for API key
                has_auth, auth_path = self.check_auth_files(
                    config_dir, config.get("auth_files", [])
                )
                if has_auth:
                    status.auth_status = "authenticated"
                    status.auth_details = f"Config found at {auth_path.name}"
                else:
                    status.auth_status = "unauthenticated"
                    status.auth_details = "No API key found"
                    env_list = ", ".join(env_vars) if env_vars else "API key"
                    status.fix_instructions = f"Set {env_list} environment variable or configure in {config_dir}"
            else:
                status.auth_status = "unauthenticated"
                status.auth_details = "Platform not configured"
                if env_vars:
                    status.fix_instructions = f"Set {env_vars[0]} environment variable"

        else:
            status.auth_status = "not_applicable"

        return status

    def check_all_platforms(self) -> ConnectionStatus:
        """Check status of all platforms."""
        result = ConnectionStatus()

        for platform_id in self.PLATFORMS:
            status = self.check_platform(platform_id)
            result.platforms.append(status)

            # Count status
            if status.auth_status == "authenticated" and status.cli_available:
                result.healthy_count += 1
            elif status.auth_status == "unauthenticated":
                if status.installed:
                    result.warning_count += 1
                else:
                    # Not installed is not an error
                    pass
            elif status.error:
                result.error_count += 1

        result.last_checked = datetime.now().isoformat()
        return result

    def get_platform_fix_command(self, platform_id: str) -> Optional[str]:
        """Get the CLI command to fix authentication for a platform."""
        if platform_id not in self.PLATFORMS:
            return None

        config = self.PLATFORMS[platform_id]
        cli = config["cli"]
        auth_method = config.get("auth_method")

        if auth_method == "oauth":
            if platform_id == "copilot":
                return "gh auth login"
            return f"{cli} login"
        elif auth_method == "api_key":
            env_vars = config.get("env_vars", [])
            if env_vars:
                return f"export {env_vars[0]}=your_api_key"
        return None

    def to_dict(self, status: ConnectionStatus) -> dict:
        """Convert ConnectionStatus to dictionary for JSON serialization."""
        return {
            "last_checked": status.last_checked,
            "healthy_count": status.healthy_count,
            "warning_count": status.warning_count,
            "error_count": status.error_count,
            "platforms": [
                {
                    "name": p.name,
                    "cli_name": p.cli_name,
                    "installed": p.installed,
                    "cli_available": p.cli_available,
                    "cli_version": p.cli_version,
                    "config_exists": p.config_exists,
                    "config_path": str(p.config_path) if p.config_path else None,
                    "auth_status": p.auth_status,
                    "auth_method": p.auth_method,
                    "auth_details": p.auth_details,
                    "last_checked": p.last_checked,
                    "error": p.error,
                    "fix_instructions": p.fix_instructions,
                }
                for p in status.platforms
            ]
        }
