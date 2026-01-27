"""
Version Tracker - Tracks platform versions and detects changes.
Stores state in ~/.claude/.platform_versions.json
"""

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class PlatformHealth:
    """Health status for a platform."""
    status: str  # "healthy", "warning", "error", "unknown"
    issues: list[str] = field(default_factory=list)
    last_check: Optional[str] = None


@dataclass
class PlatformVersion:
    """Version information for a platform."""
    platform_id: str
    version_detected: Optional[str] = None
    config_format_hash: Optional[str] = None
    last_sync_success: Optional[str] = None
    health: PlatformHealth = field(default_factory=lambda: PlatformHealth(status="unknown"))


@dataclass
class Alert:
    """An alert about platform changes."""
    platform: str
    severity: str  # "info", "warning", "error"
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False


class VersionTracker:
    """
    Tracks platform versions, config hashes, and sync state.
    Detects changes and generates alerts.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, state_file: Optional[Path] = None):
        self.home = Path.home()
        self.state_file = state_file or (self.home / ".claude" / ".platform_versions.json")
        self.platforms: dict[str, PlatformVersion] = {}
        self.alerts: list[Alert] = []
        self.last_checked: Optional[str] = None
        self._load_state()

    def _load_state(self) -> None:
        """Load saved state from JSON file."""
        if not self.state_file.exists():
            return

        try:
            data = json.loads(self.state_file.read_text())
            self.last_checked = data.get("last_checked")

            for pid, pdata in data.get("platforms", {}).items():
                health_data = pdata.get("health", {})
                self.platforms[pid] = PlatformVersion(
                    platform_id=pid,
                    version_detected=pdata.get("version_detected"),
                    config_format_hash=pdata.get("config_format_hash"),
                    last_sync_success=pdata.get("last_sync_success"),
                    health=PlatformHealth(
                        status=health_data.get("status", "unknown"),
                        issues=health_data.get("issues", []),
                        last_check=health_data.get("last_check"),
                    ),
                )

            for alert_data in data.get("alerts", []):
                self.alerts.append(Alert(
                    platform=alert_data["platform"],
                    severity=alert_data["severity"],
                    message=alert_data["message"],
                    timestamp=alert_data.get("timestamp", ""),
                    acknowledged=alert_data.get("acknowledged", False),
                ))
        except Exception:
            pass

    def save_state(self) -> None:
        """Save current state to JSON file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "schema_version": self.SCHEMA_VERSION,
            "last_checked": self.last_checked,
            "platforms": {},
            "alerts": [],
        }

        for pid, pv in self.platforms.items():
            data["platforms"][pid] = {
                "version_detected": pv.version_detected,
                "config_format_hash": pv.config_format_hash,
                "last_sync_success": pv.last_sync_success,
                "health": {
                    "status": pv.health.status,
                    "issues": pv.health.issues,
                    "last_check": pv.health.last_check,
                },
            }

        for alert in self.alerts[-50:]:  # Keep last 50 alerts
            data["alerts"].append({
                "platform": alert.platform,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "acknowledged": alert.acknowledged,
            })

        self.state_file.write_text(json.dumps(data, indent=2))

    def detect_cli_version(self, cli_command: str) -> Optional[str]:
        """Detect version from CLI --version output."""
        if not cli_command:
            return None

        try:
            result = subprocess.run(
                cli_command.split(),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Extract version from output (usually first line, last word)
                output = result.stdout.strip() or result.stderr.strip()
                if output:
                    # Common patterns: "tool v1.2.3", "tool 1.2.3", "version 1.2.3"
                    parts = output.split()
                    for part in reversed(parts):
                        # Look for version-like strings
                        clean = part.lstrip('v').rstrip(',.')
                        if any(c.isdigit() for c in clean):
                            return clean
                    return output[:50]  # Fallback: first 50 chars
        except Exception:
            pass
        return None

    def compute_config_hash(self, config_path: Path) -> Optional[str]:
        """Compute hash of a config file for change detection."""
        if not config_path or not config_path.exists():
            return None

        try:
            if config_path.is_file():
                content = config_path.read_bytes()
            elif config_path.is_dir():
                # Hash directory structure
                files = sorted(config_path.rglob("*"))
                content = b""
                for f in files[:100]:  # Limit to first 100 files
                    if f.is_file():
                        content += f.name.encode() + f.read_bytes()
            else:
                return None

            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return None

    def check_platform(self, platform_id: str, cli_check: Optional[str],
                       config_path: Optional[Path]) -> PlatformVersion:
        """Check a platform's current version and state."""
        current = self.platforms.get(platform_id)
        if not current:
            current = PlatformVersion(platform_id=platform_id)
            self.platforms[platform_id] = current

        old_version = current.version_detected
        old_hash = current.config_format_hash

        # Detect version
        if cli_check:
            current.version_detected = self.detect_cli_version(cli_check)

        # Compute config hash
        if config_path:
            current.config_format_hash = self.compute_config_hash(config_path)

        # Update health
        issues = []
        if cli_check and not current.version_detected:
            issues.append("CLI not detected or version check failed")
        if config_path and not config_path.exists():
            issues.append("Config directory not found")

        current.health = PlatformHealth(
            status="healthy" if not issues else "warning",
            issues=issues,
            last_check=datetime.now().isoformat(),
        )

        # Generate alerts for changes
        if old_version and current.version_detected and old_version != current.version_detected:
            self.add_alert(
                platform_id,
                "info",
                f"Version changed: {old_version} -> {current.version_detected}",
            )

        if old_hash and current.config_format_hash and old_hash != current.config_format_hash:
            self.add_alert(
                platform_id,
                "warning",
                "Config format changed - sync may need updating",
            )

        return current

    def add_alert(self, platform: str, severity: str, message: str) -> None:
        """Add a new alert."""
        self.alerts.append(Alert(
            platform=platform,
            severity=severity,
            message=message,
        ))

    def get_unacknowledged_alerts(self) -> list[Alert]:
        """Get alerts that haven't been acknowledged."""
        return [a for a in self.alerts if not a.acknowledged]

    def acknowledge_all_alerts(self) -> int:
        """Acknowledge all current alerts. Returns count."""
        count = 0
        for alert in self.alerts:
            if not alert.acknowledged:
                alert.acknowledged = True
                count += 1
        return count

    def record_sync_success(self, platform_id: str) -> None:
        """Record a successful sync for a platform."""
        if platform_id not in self.platforms:
            self.platforms[platform_id] = PlatformVersion(platform_id=platform_id)
        self.platforms[platform_id].last_sync_success = datetime.now().isoformat()

    def get_platform_status(self, platform_id: str) -> dict:
        """Get status summary for a platform."""
        pv = self.platforms.get(platform_id)
        if not pv:
            return {"status": "unknown", "version": None, "last_sync": None}

        return {
            "status": pv.health.status,
            "version": pv.version_detected,
            "last_sync": pv.last_sync_success,
            "issues": pv.health.issues,
        }

    def check_all(self, registry) -> dict[str, PlatformVersion]:
        """Check all platforms from registry."""
        self.last_checked = datetime.now().isoformat()

        for pid, config in registry.all().items():
            self.check_platform(
                pid,
                config.cli_check,
                config.global_config,
            )

        self.save_state()
        return self.platforms

    def get_summary(self) -> dict:
        """Get a summary of all platforms."""
        healthy = sum(1 for p in self.platforms.values() if p.health.status == "healthy")
        warning = sum(1 for p in self.platforms.values() if p.health.status == "warning")
        error = sum(1 for p in self.platforms.values() if p.health.status == "error")
        unknown = sum(1 for p in self.platforms.values() if p.health.status == "unknown")
        pending_alerts = len(self.get_unacknowledged_alerts())

        return {
            "total": len(self.platforms),
            "healthy": healthy,
            "warning": warning,
            "error": error,
            "unknown": unknown,
            "pending_alerts": pending_alerts,
            "last_checked": self.last_checked,
        }
