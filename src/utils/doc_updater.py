"""
Doc Updater - Auto-updates documentation based on compatibility checks.
Updates platform-feature-matrix.md and compatibility-log.md.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FeatureMatrix:
    """Platform feature matrix data."""
    platforms: dict[str, dict[str, bool]]
    last_updated: str


class DocUpdater:
    """
    Automatically updates documentation files based on validation results.
    """

    def __init__(self, docs_dir: Optional[Path] = None):
        self.docs_dir = docs_dir or Path.cwd() / "docs"

    def update_feature_matrix(self, registry, validation_results: dict) -> bool:
        """Update the platform feature matrix documentation."""
        matrix_file = self.docs_dir / "platform-feature-matrix.md"

        # Build feature data
        features = [
            "skills", "agents", "hooks", "mcp", "commands",
            "plugins", "rules", "workflows", "steering"
        ]

        platforms_data = {}
        for pid, config in registry.all().items():
            platforms_data[pid] = {
                "name": config.name,
                "features": {f: f in config.features for f in features},
                "skill_format": config.skill_format,
                "frontmatter": config.frontmatter,
            }

        # Generate markdown table
        content = self._generate_matrix_markdown(platforms_data, features)

        # Write file
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        matrix_file.write_text(content)
        return True

    def _generate_matrix_markdown(self, platforms_data: dict, features: list) -> str:
        """Generate markdown content for feature matrix."""
        lines = [
            "# Platform Feature Matrix",
            "",
            f"> Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "> Do not edit manually - run `python3 sync_agents.py --compat update-docs`",
            "",
            "## Feature Support",
            "",
        ]

        # Header row
        header = "| Platform | " + " | ".join(f.title() for f in features) + " | Format |"
        separator = "|" + "|".join("-" * 10 for _ in range(len(features) + 2)) + "|"

        lines.append(header)
        lines.append(separator)

        # Data rows
        for pid, data in sorted(platforms_data.items(), key=lambda x: x[1]["name"]):
            row = f"| {data['name']} |"
            for f in features:
                supported = data["features"].get(f, False)
                row += " + |" if supported else " - |"
            row += f" {data['skill_format']} |"
            lines.append(row)

        lines.extend([
            "",
            "## Legend",
            "- `+` = Supported",
            "- `-` = Not supported",
            "",
            "## Sync Compatibility",
            "",
            "### SKILL.md Compatible (direct copy)",
            "",
        ])

        skill_md = [pid for pid, d in platforms_data.items() if d["skill_format"] == "SKILL.md"]
        for pid in skill_md:
            lines.append(f"- {platforms_data[pid]['name']}")

        lines.extend([
            "",
            "### Requires Conversion",
            "",
        ])

        conversion = [pid for pid, d in platforms_data.items() if d["skill_format"] != "SKILL.md"]
        for pid in conversion:
            lines.append(f"- {platforms_data[pid]['name']} ({platforms_data[pid]['skill_format']})")

        lines.extend([
            "",
            "<!-- MACHINE_READABLE_START",
            json.dumps(platforms_data, indent=2),
            "MACHINE_READABLE_END -->",
            "",
        ])

        return "\n".join(lines)

    def append_compatibility_log(self, entry: dict) -> bool:
        """Append an entry to the compatibility log."""
        log_file = self.docs_dir / "compatibility-log.md"

        # Create file if doesn't exist
        if not log_file.exists():
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            log_file.write_text(self._get_log_header())

        # Format entry
        timestamp = entry.get("timestamp", datetime.now().isoformat())
        platform = entry.get("platform", "unknown")
        event_type = entry.get("type", "info")
        message = entry.get("message", "")
        details = entry.get("details", "")

        # Build details block separately (avoid backslash in f-string)
        details_block = ""
        if details:
            details_block = "```\n" + details + "\n```"

        entry_text = f"""
### {timestamp[:10]} - {platform.title()}

**Type:** {event_type}

{message}

{details_block}

---
"""

        # Append to file
        with open(log_file, "a") as f:
            f.write(entry_text)

        return True

    def _get_log_header(self) -> str:
        """Get header template for compatibility log."""
        return f"""# Compatibility Log

> Auto-generated changelog tracking platform compatibility changes.
> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Format

Each entry contains:
- **Timestamp** - When the change was detected
- **Platform** - Which platform is affected
- **Type** - info, warning, error, breaking
- **Message** - Description of the change

---

"""

    def log_version_change(self, platform_id: str, old_version: str, new_version: str) -> bool:
        """Log a version change event."""
        return self.append_compatibility_log({
            "timestamp": datetime.now().isoformat(),
            "platform": platform_id,
            "type": "info",
            "message": f"Version updated from {old_version} to {new_version}",
        })

    def log_sync_result(self, platform_id: str, success: bool, details: str = "") -> bool:
        """Log a sync operation result."""
        return self.append_compatibility_log({
            "timestamp": datetime.now().isoformat(),
            "platform": platform_id,
            "type": "info" if success else "error",
            "message": f"Sync {'succeeded' if success else 'failed'}",
            "details": details,
        })

    def log_breaking_change(self, platform_id: str, description: str, migration: str = "") -> bool:
        """Log a breaking change that requires user action."""
        return self.append_compatibility_log({
            "timestamp": datetime.now().isoformat(),
            "platform": platform_id,
            "type": "breaking",
            "message": f"BREAKING CHANGE: {description}",
            "details": migration if migration else "Check platform documentation for migration steps.",
        })

    def update_research_log(self, findings: list[dict]) -> bool:
        """Update the research log with new findings."""
        research_file = self.docs_dir / "RESEARCH_LOG.md"

        if not research_file.exists():
            content = f"""# Platform Research Log

> Tracking research findings for AI coding platforms.
> Last updated: {datetime.now().strftime('%Y-%m-%d')}

---

"""
        else:
            content = research_file.read_text()

        # Add new findings
        for finding in findings:
            entry = f"""
## {finding.get('date', datetime.now().strftime('%Y-%m-%d'))} - {finding.get('platform', 'General')}

**Topic:** {finding.get('topic', 'N/A')}

{finding.get('content', '')}

**Source:** {finding.get('source', 'N/A')}

---
"""
            content += entry

        research_file.write_text(content)
        return True

    def generate_sync_report(self, results: dict) -> str:
        """Generate a sync operation report."""
        lines = [
            f"# Sync Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
        ]

        successful = [p for p, r in results.items() if r.get("success", False)]
        failed = [p for p, r in results.items() if not r.get("success", False)]

        lines.append(f"- **Successful:** {len(successful)}")
        lines.append(f"- **Failed:** {len(failed)}")
        lines.append("")

        if successful:
            lines.append("## Successful Syncs")
            lines.append("")
            for p in successful:
                lines.append(f"- {p}: {results[p].get('details', 'OK')}")
            lines.append("")

        if failed:
            lines.append("## Failed Syncs")
            lines.append("")
            for p in failed:
                lines.append(f"- {p}: {results[p].get('error', 'Unknown error')}")
            lines.append("")

        return "\n".join(lines)

    def read_machine_readable_data(self, file_path: Path) -> Optional[dict]:
        """Read machine-readable data from a markdown file."""
        if not file_path.exists():
            return None

        content = file_path.read_text()

        match = re.search(
            r'<!-- MACHINE_READABLE_START\s*(.*?)\s*MACHINE_READABLE_END -->',
            content,
            re.DOTALL
        )

        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None

        return None
