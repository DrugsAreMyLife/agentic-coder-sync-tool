"""
Compatibility Validator - Validates sync operations before execution.
Provides dry-run validation, backup/restore, and format checking.
"""

import hashlib
import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ValidationResult:
    """Result of a validation check."""
    platform_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)


@dataclass
class BackupInfo:
    """Information about a backup."""
    path: Path
    platform_id: str
    timestamp: str
    size_bytes: int
    components: list[str]


class CompatibilityValidator:
    """
    Validates sync compatibility and manages backups.
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        self.home = Path.home()
        self.backup_dir = backup_dir or (self.home / ".claude" / ".sync_backups")

    def validate_source(self, syncer) -> ValidationResult:
        """Validate Claude Code source configuration."""
        result = ValidationResult(platform_id="claude", valid=True)

        # Check Claude directory exists
        claude_dir = self.home / ".claude"
        if not claude_dir.exists():
            result.errors.append("Claude Code directory not found (~/.claude)")
            result.valid = False
            return result

        # Check for components
        if not syncer.agents:
            result.warnings.append("No agents found")
        else:
            result.info.append(f"Found {len(syncer.agents)} agents")

        if not syncer.skills:
            result.warnings.append("No skills found")
        else:
            result.info.append(f"Found {len(syncer.skills)} skills")

        if not syncer.commands:
            result.info.append("No custom commands found")
        else:
            result.info.append(f"Found {len(syncer.commands)} commands")

        if not syncer.hooks:
            result.info.append("No hooks configured")
        else:
            result.info.append(f"Found {len(syncer.hooks)} hooks")

        # Validate skill structure
        for skill in syncer.skills:
            skill_md = skill.source_path / "SKILL.md"
            if not skill_md.exists():
                result.warnings.append(f"Skill '{skill.name}' missing SKILL.md")

        # Validate agent frontmatter
        for agent in syncer.agents:
            if not agent.tools:
                result.warnings.append(f"Agent '{agent.name}' has no tools defined")

        return result

    def validate_target(self, platform_id: str, platform_config) -> ValidationResult:
        """Validate a target platform is ready for sync."""
        result = ValidationResult(platform_id=platform_id, valid=True)

        # Check if platform is installed
        if platform_config.global_config:
            if not platform_config.global_config.exists():
                result.warnings.append(f"Platform directory not found: {platform_config.global_config}")
                # Not an error - we can create it
            else:
                result.info.append(f"Platform directory exists: {platform_config.global_config}")

        # Check for existing content that would be overwritten
        if platform_config.skills_path and platform_config.skills_path.exists():
            skill_count = sum(1 for d in platform_config.skills_path.iterdir() if d.is_dir())
            if skill_count > 0:
                result.info.append(f"Will update {skill_count} existing skills")

        # Check write permissions
        target_dir = platform_config.skills_path or platform_config.global_config
        if target_dir:
            parent = target_dir.parent if not target_dir.exists() else target_dir
            while parent and not parent.exists():
                parent = parent.parent
            if parent:
                try:
                    test_file = parent / ".sync_test_write"
                    test_file.touch()
                    test_file.unlink()
                    result.info.append("Write permission verified")
                except PermissionError:
                    result.errors.append(f"No write permission to {parent}")
                    result.valid = False
                except Exception:
                    pass

        return result

    def dry_run_sync(self, syncer, platform_id: str, platform_config) -> ValidationResult:
        """Perform a dry-run sync to validate without making changes."""
        result = ValidationResult(platform_id=platform_id, valid=True)

        # Validate source first
        source_result = self.validate_source(syncer)
        result.errors.extend(source_result.errors)
        result.warnings.extend(source_result.warnings)
        if not source_result.valid:
            result.valid = False
            return result

        # Validate target
        target_result = self.validate_target(platform_id, platform_config)
        result.errors.extend(target_result.errors)
        result.warnings.extend(target_result.warnings)
        result.info.extend(target_result.info)
        if not target_result.valid:
            result.valid = False
            return result

        # Simulate sync operations
        operations = []

        # Skills
        if platform_config.skills_path:
            for skill in syncer.skills:
                target = platform_config.skills_path / skill.name
                if target.exists():
                    operations.append(f"UPDATE: {skill.name} skill")
                else:
                    operations.append(f"CREATE: {skill.name} skill")

        # Agents (converted to skills on most platforms)
        if platform_config.skills_path and syncer.agents:
            agents_dir = platform_config.skills_path / "_claude_agents"
            for agent in syncer.agents:
                operations.append(f"CREATE: {agent.name} agent-skill")

        if operations:
            result.info.append(f"Planned operations: {len(operations)}")
            for op in operations[:10]:
                result.info.append(f"  - {op}")
            if len(operations) > 10:
                result.info.append(f"  ... and {len(operations) - 10} more")

        return result

    def create_backup(self, platform_id: str, platform_config) -> Optional[BackupInfo]:
        """Create a backup of platform configuration before sync."""
        if not platform_config.global_config or not platform_config.global_config.exists():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{platform_id}-{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name

        components = []

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                # Backup skills
                if platform_config.skills_path and platform_config.skills_path.exists():
                    tar.add(platform_config.skills_path, arcname="skills")
                    components.append("skills")

                # Backup MCP config
                if platform_config.mcp_path and platform_config.mcp_path.exists():
                    tar.add(platform_config.mcp_path, arcname=platform_config.mcp_path.name)
                    components.append("mcp")

                # Backup hooks
                if platform_config.hooks_path and platform_config.hooks_path.exists():
                    tar.add(platform_config.hooks_path, arcname=platform_config.hooks_path.name)
                    components.append("hooks")

            return BackupInfo(
                path=backup_path,
                platform_id=platform_id,
                timestamp=timestamp,
                size_bytes=backup_path.stat().st_size,
                components=components,
            )
        except Exception:
            if backup_path.exists():
                backup_path.unlink()
            return None

    def restore_backup(self, backup_info: BackupInfo, platform_config) -> bool:
        """Restore a platform from backup."""
        if not backup_info.path.exists():
            return False

        try:
            with tarfile.open(backup_info.path, "r:gz") as tar:
                # Extract to temp directory first
                with tempfile.TemporaryDirectory() as tmpdir:
                    tar.extractall(tmpdir)
                    extracted = Path(tmpdir)

                    # Restore skills
                    skills_backup = extracted / "skills"
                    if skills_backup.exists() and platform_config.skills_path:
                        if platform_config.skills_path.exists():
                            shutil.rmtree(platform_config.skills_path)
                        shutil.copytree(skills_backup, platform_config.skills_path)

                    # Restore MCP
                    for mcp_name in ["mcp.json", "settings.json", ".mcp.json"]:
                        mcp_backup = extracted / mcp_name
                        if mcp_backup.exists() and platform_config.mcp_path:
                            shutil.copy2(mcp_backup, platform_config.mcp_path)
                            break

                    # Restore hooks
                    for hooks_name in ["hooks.json", "hooks"]:
                        hooks_backup = extracted / hooks_name
                        if hooks_backup.exists() and platform_config.hooks_path:
                            if hooks_backup.is_dir():
                                if platform_config.hooks_path.exists():
                                    shutil.rmtree(platform_config.hooks_path)
                                shutil.copytree(hooks_backup, platform_config.hooks_path)
                            else:
                                shutil.copy2(hooks_backup, platform_config.hooks_path)
                            break

            return True
        except Exception:
            return False

    def list_backups(self, platform_id: Optional[str] = None) -> list[BackupInfo]:
        """List available backups, optionally filtered by platform."""
        if not self.backup_dir.exists():
            return []

        backups = []
        for backup_file in self.backup_dir.glob("*.tar.gz"):
            try:
                parts = backup_file.stem.split("-")
                if len(parts) >= 3:
                    pid = parts[0]
                    ts = "-".join(parts[1:])

                    if platform_id and pid != platform_id:
                        continue

                    backups.append(BackupInfo(
                        path=backup_file,
                        platform_id=pid,
                        timestamp=ts,
                        size_bytes=backup_file.stat().st_size,
                        components=[],  # Would need to read tar to know
                    ))
            except Exception:
                continue

        return sorted(backups, key=lambda b: b.timestamp, reverse=True)

    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """Remove old backups, keeping only the most recent per platform."""
        if not self.backup_dir.exists():
            return 0

        # Group by platform
        by_platform: dict[str, list[BackupInfo]] = {}
        for backup in self.list_backups():
            by_platform.setdefault(backup.platform_id, []).append(backup)

        removed = 0
        for pid, backups in by_platform.items():
            # Sort by timestamp (newest first)
            sorted_backups = sorted(backups, key=lambda b: b.timestamp, reverse=True)
            for backup in sorted_backups[keep_count:]:
                try:
                    backup.path.unlink()
                    removed += 1
                except Exception:
                    pass

        return removed

    def compare_configs(self, config1_path: Path, config2_path: Path) -> dict:
        """Compare two config files/directories and report differences."""
        result = {
            "identical": True,
            "config1_only": [],
            "config2_only": [],
            "modified": [],
            "unchanged": [],
        }

        def get_file_hash(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        def get_files(base: Path) -> dict[str, str]:
            files = {}
            if base.is_file():
                files[base.name] = get_file_hash(base)
            elif base.is_dir():
                for f in base.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(base))
                        files[rel] = get_file_hash(f)
            return files

        try:
            files1 = get_files(config1_path) if config1_path.exists() else {}
            files2 = get_files(config2_path) if config2_path.exists() else {}

            all_files = set(files1.keys()) | set(files2.keys())

            for f in all_files:
                if f in files1 and f in files2:
                    if files1[f] == files2[f]:
                        result["unchanged"].append(f)
                    else:
                        result["modified"].append(f)
                        result["identical"] = False
                elif f in files1:
                    result["config1_only"].append(f)
                    result["identical"] = False
                else:
                    result["config2_only"].append(f)
                    result["identical"] = False

        except Exception as e:
            result["error"] = str(e)
            result["identical"] = False

        return result
