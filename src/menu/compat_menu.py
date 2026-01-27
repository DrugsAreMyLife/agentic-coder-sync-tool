"""Compatibility Check Menu for platform validation and monitoring."""

import sys
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from menu.base import BaseMenu


class CompatMenu(BaseMenu):
    """Interactive compatibility check and platform monitoring menu."""

    def __init__(self, syncer):
        super().__init__()
        self.syncer = syncer

        # Lazy imports to avoid circular dependencies
        from utils.platform_registry import get_registry
        from utils.version_tracker import VersionTracker
        from utils.compat_validator import CompatibilityValidator
        from utils.web_monitor import WebMonitor
        from utils.doc_updater import DocUpdater

        self.registry = get_registry()
        self.tracker = VersionTracker()
        self.validator = CompatibilityValidator()
        self.monitor = WebMonitor()
        self.doc_updater = DocUpdater()

    def run(self) -> Optional[str]:
        """Run the compatibility menu loop."""
        while True:
            self.clear_screen()
            self._draw_menu()

            choice = self.prompt()

            if choice.lower() == 'q':
                return None
            elif choice == '1':
                self._quick_check()
            elif choice == '2':
                self._full_validation()
            elif choice == '3':
                self._check_documentation()
            elif choice == '4':
                self._view_alerts()
            elif choice == '5':
                self._manage_backups()
            elif choice == '6':
                self._update_docs()
            elif choice == '7':
                self._platform_details()

    def _draw_menu(self) -> None:
        """Draw the compatibility menu."""
        c = self.colors
        b = self.box

        self.draw_box("COMPATIBILITY CHECK")

        # Show summary
        summary = self.tracker.get_summary()
        pending_alerts = summary.get("pending_alerts", 0)

        print(f"  Platforms tracked: {summary.get('total', 0)}")
        status_line = f"  Status: {c.colorize(str(summary.get('healthy', 0)), c.GREEN)} healthy"
        if summary.get("warning", 0):
            status_line += f" | {c.colorize(str(summary['warning']), c.YELLOW)} warning"
        if summary.get("error", 0):
            status_line += f" | {c.colorize(str(summary['error']), c.RED)} error"
        print(status_line)

        if pending_alerts > 0:
            print(f"  {c.colorize(f'[!] {pending_alerts} pending alerts', c.YELLOW, c.BOLD)}")
        print()

        # Menu options
        self.draw_option("1", "Quick Check", "Check all platforms status")
        print()
        self.draw_option("2", "Full Validation", "Dry-run sync validation")
        print()
        self.draw_option("3", "Check Documentation", "Monitor docs for changes")
        print()
        self.draw_option("4", "View Alerts", "See pending compatibility alerts")
        print()
        self.draw_option("5", "Manage Backups", "View and restore backups")
        print()
        self.draw_option("6", "Update Docs", "Regenerate feature matrix")
        print()
        self.draw_option("7", "Platform Details", "View single platform info")
        print()
        self.draw_option("q", "Back")

    def _quick_check(self) -> None:
        """Run quick status check on all platforms."""
        self.clear_screen()
        self.draw_box("QUICK CHECK")

        c = self.colors
        b = self.box

        print("  Checking platforms...")
        print()

        results = self.tracker.check_all(self.registry)

        # Display results table
        print(f"  {'Platform':<20} {'Status':<12} {'Version':<15} {'Last Sync'}")
        print(f"  {'-' * 65}")

        for pid, pv in sorted(results.items(), key=lambda x: x[0]):
            config = self.registry.get(pid)
            name = config.name if config else pid

            status = pv.health.status
            if status == "healthy":
                status_display = c.colorize("healthy", c.GREEN)
            elif status == "warning":
                status_display = c.colorize("warning", c.YELLOW)
            elif status == "error":
                status_display = c.colorize("error", c.RED)
            else:
                status_display = c.colorize("unknown", c.DIM)

            version = pv.version_detected or "-"
            last_sync = pv.last_sync_success[:10] if pv.last_sync_success else "never"

            print(f"  {name:<20} {status_display:<20} {version:<15} {last_sync}")

            # Show issues
            for issue in pv.health.issues[:2]:
                print(f"    {c.colorize(f'- {issue}', c.DIM)}")

        self.wait_for_key()

    def _full_validation(self) -> None:
        """Run full validation for all platforms."""
        self.clear_screen()
        self.draw_box("FULL VALIDATION")

        c = self.colors

        print("  Running dry-run validation...")
        print()

        # Validate source
        source_result = self.validator.validate_source(self.syncer)
        print(f"  {c.colorize('Source (Claude Code):', c.BOLD)}")

        if source_result.valid:
            self.print_success("Source configuration valid")
        else:
            self.print_error("Source configuration has issues")

        for error in source_result.errors:
            print(f"    {c.colorize('ERROR:', c.RED)} {error}")
        for warning in source_result.warnings:
            print(f"    {c.colorize('WARN:', c.YELLOW)} {warning}")
        for info in source_result.info[:5]:
            print(f"    {c.colorize('INFO:', c.DIM)} {info}")

        print()

        # Validate each platform
        for pid, config in list(self.registry.all().items())[:6]:  # First 6 platforms
            print(f"  {c.colorize(f'{config.name}:', c.BOLD)}")

            result = self.validator.dry_run_sync(self.syncer, pid, config)

            if result.valid:
                self.print_success(f"Ready for sync")
            else:
                self.print_error(f"Issues detected")

            for error in result.errors[:2]:
                print(f"    {c.colorize('ERROR:', c.RED)} {error}")
            for warning in result.warnings[:2]:
                print(f"    {c.colorize('WARN:', c.YELLOW)} {warning}")

        self.wait_for_key()

    def _check_documentation(self) -> None:
        """Check documentation URLs for changes."""
        self.clear_screen()
        self.draw_box("DOCUMENTATION CHECK")

        c = self.colors

        print("  Fetching documentation pages...")
        print("  (This may take a moment)")
        print()

        results = self.monitor.check_all_platforms(self.registry)

        # Show results
        print(f"  {'Platform':<20} {'Docs':<10} {'Changelog':<10} {'Version'}")
        print(f"  {'-' * 55}")

        for pid in sorted(self.registry.all().keys()):
            config = self.registry.get(pid)
            name = config.name if config else pid

            docs_result = results.get(pid)
            changelog_result = results.get(f"{pid}_changelog")

            docs_status = c.colorize("OK", c.GREEN) if docs_result and docs_result.success else c.colorize("FAIL", c.RED)
            cl_status = c.colorize("OK", c.GREEN) if changelog_result and changelog_result.success else c.colorize("-", c.DIM)

            version = ""
            if docs_result and docs_result.version_detected:
                version = docs_result.version_detected

            print(f"  {name:<20} {docs_status:<18} {cl_status:<18} {version}")

        # Show recent changes
        recent = self.monitor.get_recent_changes(7)
        if recent:
            print()
            self.draw_section("Recent Changes (7 days):")
            for change in recent[:5]:
                print(f"  - {change.platform_id}: {change.change_type} change detected")

        self.wait_for_key()

    def _view_alerts(self) -> None:
        """View and manage alerts."""
        self.clear_screen()
        self.draw_box("ALERTS")

        c = self.colors

        alerts = self.tracker.get_unacknowledged_alerts()

        if not alerts:
            print(f"  {c.colorize('No pending alerts', c.DIM)}")
        else:
            for i, alert in enumerate(alerts, 1):
                severity_color = {
                    "info": c.CYAN,
                    "warning": c.YELLOW,
                    "error": c.RED,
                }.get(alert.severity, c.WHITE)

                print(f"  [{i}] {c.colorize(alert.severity.upper(), severity_color)} - {alert.platform}")
                print(f"      {alert.message}")
                print(f"      {c.colorize(alert.timestamp[:16], c.DIM)}")
                print()

            print()
            if self.prompt_confirm("Acknowledge all alerts?"):
                count = self.tracker.acknowledge_all_alerts()
                self.tracker.save_state()
                self.print_success(f"Acknowledged {count} alerts")

        self.wait_for_key()

    def _manage_backups(self) -> None:
        """Manage platform backups."""
        self.clear_screen()
        self.draw_box("BACKUP MANAGEMENT")

        c = self.colors

        backups = self.validator.list_backups()

        if not backups:
            print(f"  {c.colorize('No backups found', c.DIM)}")
            print()
            print("  Backups are created automatically before risky sync operations.")
        else:
            print(f"  Found {len(backups)} backups:")
            print()
            print(f"  {'#':<4} {'Platform':<15} {'Date':<20} {'Size'}")
            print(f"  {'-' * 50}")

            for i, backup in enumerate(backups[:10], 1):
                size_kb = backup.size_bytes / 1024
                print(f"  [{i}] {backup.platform_id:<15} {backup.timestamp:<20} {size_kb:.1f} KB")

            print()
            print(f"  {c.colorize('[c] Cleanup old backups', c.DIM)}  {c.colorize('[r] Restore', c.DIM)}")

            choice = self.prompt()
            if choice.lower() == 'c':
                removed = self.validator.cleanup_old_backups(keep_count=3)
                self.print_success(f"Removed {removed} old backups")
                self.wait_for_key()
            elif choice.lower() == 'r':
                self.print_info("Select backup number to restore")
                # Restore logic would go here

        self.wait_for_key()

    def _update_docs(self) -> None:
        """Update documentation files."""
        self.clear_screen()
        self.draw_box("UPDATE DOCUMENTATION")

        print("  This will regenerate:")
        print("  - docs/platform-feature-matrix.md")
        print("  - Append to docs/compatibility-log.md")
        print()

        if self.prompt_confirm("Proceed?"):
            try:
                self.doc_updater.update_feature_matrix(self.registry, {})
                self.print_success("Updated platform-feature-matrix.md")

                self.doc_updater.append_compatibility_log({
                    "type": "info",
                    "platform": "all",
                    "message": "Feature matrix regenerated",
                })
                self.print_success("Updated compatibility-log.md")
            except Exception as e:
                self.print_error(f"Failed: {e}")

        self.wait_for_key()

    def _platform_details(self) -> None:
        """View detailed info for a single platform."""
        self.clear_screen()
        self.draw_box("PLATFORM DETAILS")

        c = self.colors

        # List platforms
        platforms = list(self.registry.all().keys())
        for i, pid in enumerate(platforms, 1):
            config = self.registry.get(pid)
            print(f"  [{i}] {config.name}")

        print()
        choice = self.prompt("Select platform")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(platforms):
                pid = platforms[idx]
                self._show_platform_detail(pid)
        except ValueError:
            pass

    def _show_platform_detail(self, platform_id: str) -> None:
        """Show detailed information for a platform."""
        self.clear_screen()

        config = self.registry.get(platform_id)
        if not config:
            self.print_error(f"Platform not found: {platform_id}")
            self.wait_for_key()
            return

        c = self.colors
        b = self.box

        self.draw_box(f"PLATFORM: {config.name}")

        # Basic info
        self.draw_section("Configuration")
        print(f"  ID: {config.id}")
        print(f"  Skill Format: {config.skill_format}")
        print(f"  Frontmatter: {'Yes' if config.frontmatter else 'No'}")

        # Paths
        self.draw_section("Paths")
        if config.global_config:
            exists = config.global_config.exists()
            status = c.colorize(b['check'], c.GREEN) if exists else c.colorize(b['cross_mark'], c.RED)
            print(f"  {status} Config: {config.global_config}")
        if config.skills_path:
            exists = config.skills_path.exists()
            status = c.colorize(b['check'], c.GREEN) if exists else c.colorize(b['cross_mark'], c.RED)
            print(f"  {status} Skills: {config.skills_path}")
        if config.mcp_path:
            exists = config.mcp_path.exists()
            status = c.colorize(b['check'], c.GREEN) if exists else c.colorize(b['cross_mark'], c.RED)
            print(f"  {status} MCP: {config.mcp_path}")

        # Features
        self.draw_section("Features")
        print(f"  {', '.join(config.features)}")

        # Version info
        pv = self.tracker.platforms.get(platform_id)
        if pv:
            self.draw_section("Version Info")
            print(f"  Detected: {pv.version_detected or 'Unknown'}")
            print(f"  Last Sync: {pv.last_sync_success or 'Never'}")
            print(f"  Health: {pv.health.status}")

        # Documentation
        self.draw_section("Documentation")
        print(f"  Docs: {config.docs_url or 'N/A'}")
        print(f"  Changelog: {config.changelog_url or 'N/A'}")

        self.wait_for_key()
