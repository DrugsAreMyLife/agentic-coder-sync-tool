"""
Exclusion Manager - Manages private/excluded components from sync and export.
Stores exclusion rules in ~/.claude/.sync_exclusions.json
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ExclusionRule:
    """A rule defining what to exclude from sync/export."""
    id: str
    component_type: str  # "agent", "skill", "plugin", "command", "hook"
    pattern: str  # Name pattern (supports wildcards: * and ?)
    reason: str
    exclude_from_sync: bool = True
    exclude_from_export: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ExclusionManager:
    """
    Manages exclusion rules for private/confidential components.
    Components can be excluded from sync, export, or both.
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.home = Path.home()
        self.config_file = config_file or (self.home / ".claude" / ".sync_exclusions.json")
        self.rules: list[ExclusionRule] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load exclusion rules from config file."""
        if not self.config_file.exists():
            # Create default rules
            self._create_defaults()
            return

        try:
            data = json.loads(self.config_file.read_text())
            for rule_data in data.get("rules", []):
                self.rules.append(ExclusionRule(
                    id=rule_data.get("id", ""),
                    component_type=rule_data.get("component_type", ""),
                    pattern=rule_data.get("pattern", ""),
                    reason=rule_data.get("reason", ""),
                    exclude_from_sync=rule_data.get("exclude_from_sync", True),
                    exclude_from_export=rule_data.get("exclude_from_export", True),
                    created_at=rule_data.get("created_at", ""),
                ))
        except Exception:
            self._create_defaults()

    def _create_defaults(self) -> None:
        """Create default exclusion rules."""
        defaults = [
            ExclusionRule(
                id="default-private",
                component_type="*",
                pattern="*-private",
                reason="Components ending with -private are excluded by default",
            ),
            ExclusionRule(
                id="default-local",
                component_type="*",
                pattern="*-local",
                reason="Components ending with -local are excluded by default",
            ),
            ExclusionRule(
                id="default-secret",
                component_type="skill",
                pattern="*-secret*",
                reason="Skills containing 'secret' in name are excluded",
            ),
            ExclusionRule(
                id="default-personal",
                component_type="agent",
                pattern="my-*",
                reason="Agents starting with 'my-' are personal and excluded",
            ),
        ]
        self.rules = defaults
        self.save_rules()

    def save_rules(self) -> None:
        """Save rules to config file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "rules": [
                {
                    "id": rule.id,
                    "component_type": rule.component_type,
                    "pattern": rule.pattern,
                    "reason": rule.reason,
                    "exclude_from_sync": rule.exclude_from_sync,
                    "exclude_from_export": rule.exclude_from_export,
                    "created_at": rule.created_at,
                }
                for rule in self.rules
            ],
        }

        self.config_file.write_text(json.dumps(data, indent=2))

    def add_rule(self, component_type: str, pattern: str, reason: str = "",
                 exclude_sync: bool = True, exclude_export: bool = True) -> ExclusionRule:
        """Add a new exclusion rule."""
        rule_id = f"rule-{len(self.rules) + 1}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        rule = ExclusionRule(
            id=rule_id,
            component_type=component_type,
            pattern=pattern,
            reason=reason or f"User-defined exclusion for {pattern}",
            exclude_from_sync=exclude_sync,
            exclude_from_export=exclude_export,
        )

        self.rules.append(rule)
        self.save_rules()
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an exclusion rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                self.save_rules()
                return True
        return False

    def _pattern_matches(self, pattern: str, name: str) -> bool:
        """Check if a name matches a pattern (supports * and ? wildcards)."""
        # Convert glob pattern to regex
        regex_pattern = pattern.replace(".", r"\.").replace("*", ".*").replace("?", ".")
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, name, re.IGNORECASE))

    def is_excluded(self, component_type: str, name: str, context: str = "both") -> bool:
        """
        Check if a component is excluded.

        Args:
            component_type: "agent", "skill", "plugin", "command", "hook"
            name: Component name
            context: "sync", "export", or "both"
        """
        for rule in self.rules:
            # Check component type match
            if rule.component_type != "*" and rule.component_type != component_type:
                continue

            # Check pattern match
            if not self._pattern_matches(rule.pattern, name):
                continue

            # Check context
            if context == "sync" and rule.exclude_from_sync:
                return True
            if context == "export" and rule.exclude_from_export:
                return True
            if context == "both" and (rule.exclude_from_sync or rule.exclude_from_export):
                return True

        return False

    def get_exclusion_reason(self, component_type: str, name: str) -> Optional[str]:
        """Get the reason why a component is excluded."""
        for rule in self.rules:
            if rule.component_type != "*" and rule.component_type != component_type:
                continue
            if self._pattern_matches(rule.pattern, name):
                return rule.reason
        return None

    def filter_components(self, components: list, component_type: str, context: str = "both") -> tuple[list, list]:
        """
        Filter a list of components, separating included and excluded.

        Returns:
            Tuple of (included_components, excluded_components)
        """
        included = []
        excluded = []

        for component in components:
            name = getattr(component, 'name', str(component))
            if self.is_excluded(component_type, name, context):
                excluded.append(component)
            else:
                included.append(component)

        return included, excluded

    def list_rules(self) -> list[ExclusionRule]:
        """Get all exclusion rules."""
        return self.rules.copy()

    def get_rule(self, rule_id: str) -> Optional[ExclusionRule]:
        """Get a specific rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    def update_rule(self, rule_id: str, **kwargs) -> bool:
        """Update an existing rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                self.save_rules()
                return True
        return False

    def export_rules(self) -> dict:
        """Export rules to a dictionary (for sharing/backup)."""
        return {
            "version": "1.0",
            "rules": [
                {
                    "component_type": rule.component_type,
                    "pattern": rule.pattern,
                    "reason": rule.reason,
                    "exclude_from_sync": rule.exclude_from_sync,
                    "exclude_from_export": rule.exclude_from_export,
                }
                for rule in self.rules
            ],
        }

    def import_rules(self, rules_data: dict, merge: bool = True) -> int:
        """
        Import rules from a dictionary.

        Args:
            rules_data: Dictionary with rules
            merge: If True, add to existing; if False, replace

        Returns:
            Number of rules imported
        """
        if not merge:
            self.rules = []

        count = 0
        for rule_data in rules_data.get("rules", []):
            self.add_rule(
                component_type=rule_data.get("component_type", "*"),
                pattern=rule_data.get("pattern", ""),
                reason=rule_data.get("reason", ""),
                exclude_sync=rule_data.get("exclude_from_sync", True),
                exclude_export=rule_data.get("exclude_from_export", True),
            )
            count += 1

        return count

    def get_summary(self) -> dict:
        """Get summary of exclusion rules."""
        by_type = {}
        for rule in self.rules:
            by_type.setdefault(rule.component_type, []).append(rule.pattern)

        return {
            "total_rules": len(self.rules),
            "by_type": by_type,
            "sync_only": sum(1 for r in self.rules if r.exclude_from_sync and not r.exclude_from_export),
            "export_only": sum(1 for r in self.rules if r.exclude_from_export and not r.exclude_from_sync),
            "both": sum(1 for r in self.rules if r.exclude_from_sync and r.exclude_from_export),
        }

    # ========== Individual Component Exclusion Methods ==========

    def is_explicitly_excluded(self, component_type: str, name: str) -> bool:
        """
        Check if a component has an explicit (exact-match) exclusion rule.
        This differs from is_excluded() which also checks wildcard patterns.
        """
        for rule in self.rules:
            if rule.component_type not in ("*", component_type):
                continue
            # Check for exact match (not wildcard)
            if rule.pattern == name:
                return True
        return False

    def get_explicit_exclusion(self, component_type: str, name: str) -> Optional[ExclusionRule]:
        """Get the explicit exclusion rule for a specific component, if any."""
        for rule in self.rules:
            if rule.component_type not in ("*", component_type):
                continue
            if rule.pattern == name:
                return rule
        return None

    def toggle_exclusion(self, component_type: str, name: str,
                         exclude_sync: bool = True, exclude_export: bool = True) -> tuple[bool, str]:
        """
        Toggle exclusion for a specific component.

        Returns:
            Tuple of (is_now_excluded, message)
        """
        existing = self.get_explicit_exclusion(component_type, name)

        if existing:
            # Remove the exclusion
            self.remove_rule(existing.id)
            return (False, f"Removed exclusion for '{name}'")
        else:
            # Add new exclusion
            self.add_rule(
                component_type=component_type,
                pattern=name,
                reason=f"Manually excluded {component_type}",
                exclude_sync=exclude_sync,
                exclude_export=exclude_export,
            )
            return (True, f"Added exclusion for '{name}'")

    def set_exclusion(self, component_type: str, name: str, excluded: bool,
                      exclude_sync: bool = True, exclude_export: bool = True) -> str:
        """
        Explicitly set exclusion state for a component.

        Returns:
            Status message
        """
        existing = self.get_explicit_exclusion(component_type, name)

        if excluded:
            if existing:
                return f"'{name}' is already excluded"
            self.add_rule(
                component_type=component_type,
                pattern=name,
                reason=f"Manually excluded {component_type}",
                exclude_sync=exclude_sync,
                exclude_export=exclude_export,
            )
            return f"Excluded '{name}' from sync/export"
        else:
            if existing:
                self.remove_rule(existing.id)
                return f"Removed exclusion for '{name}'"
            return f"'{name}' was not explicitly excluded"

    def get_exclusion_status(self, component_type: str, name: str) -> dict:
        """
        Get detailed exclusion status for a component.

        Returns dict with:
            - is_excluded: bool (overall exclusion state)
            - is_explicit: bool (has exact-match rule)
            - matched_rule: Optional[ExclusionRule] (the rule that caused exclusion)
            - excluded_from_sync: bool
            - excluded_from_export: bool
        """
        status = {
            "is_excluded": False,
            "is_explicit": False,
            "matched_rule": None,
            "excluded_from_sync": False,
            "excluded_from_export": False,
        }

        for rule in self.rules:
            if rule.component_type not in ("*", component_type):
                continue

            if self._pattern_matches(rule.pattern, name):
                status["is_excluded"] = True
                status["matched_rule"] = rule
                status["excluded_from_sync"] = rule.exclude_from_sync
                status["excluded_from_export"] = rule.exclude_from_export

                # Check if it's an exact match (explicit)
                if rule.pattern == name:
                    status["is_explicit"] = True
                break

        return status
