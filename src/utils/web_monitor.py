"""
Web Monitor - Monitors platform documentation for changes.
Uses stdlib only (urllib.request) for fetching.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


@dataclass
class PageCheck:
    """Result of checking a documentation page."""
    url: str
    success: bool
    content_hash: Optional[str] = None
    version_detected: Optional[str] = None
    last_modified: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DocChange:
    """A detected documentation change."""
    platform_id: str
    url: str
    change_type: str  # "content", "version", "new_feature"
    old_value: Optional[str]
    new_value: Optional[str]
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


class WebMonitor:
    """
    Monitors platform documentation URLs for changes.
    Tracks content hashes and extracted versions.
    """

    # Version extraction patterns
    VERSION_PATTERNS = [
        r'version[:\s]+["\']?v?(\d+\.\d+(?:\.\d+)?)["\']?',
        r'v(\d+\.\d+(?:\.\d+)?)',
        r'release[:\s]+["\']?(\d+\.\d+(?:\.\d+)?)["\']?',
        r'(\d+\.\d+\.\d+)',
    ]

    # User agent for requests
    USER_AGENT = "AgentSyncTool/1.0 (Compatibility Monitor)"

    def __init__(self, cache_file: Optional[Path] = None):
        self.home = Path.home()
        self.cache_file = cache_file or (self.home / ".claude" / ".doc_monitor_cache.json")
        self.page_cache: dict[str, PageCheck] = {}
        self.changes: list[DocChange] = []
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached page data."""
        if not self.cache_file.exists():
            return

        try:
            data = json.loads(self.cache_file.read_text())

            for url, pdata in data.get("pages", {}).items():
                self.page_cache[url] = PageCheck(
                    url=url,
                    success=pdata.get("success", False),
                    content_hash=pdata.get("content_hash"),
                    version_detected=pdata.get("version_detected"),
                    last_modified=pdata.get("last_modified"),
                    error=pdata.get("error"),
                    timestamp=pdata.get("timestamp", ""),
                )

            for cdata in data.get("changes", []):
                self.changes.append(DocChange(
                    platform_id=cdata["platform_id"],
                    url=cdata["url"],
                    change_type=cdata["change_type"],
                    old_value=cdata.get("old_value"),
                    new_value=cdata.get("new_value"),
                    detected_at=cdata.get("detected_at", ""),
                ))
        except Exception:
            pass

    def save_cache(self) -> None:
        """Save page cache to file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "last_check": datetime.now().isoformat(),
            "pages": {},
            "changes": [],
        }

        for url, pc in self.page_cache.items():
            data["pages"][url] = {
                "success": pc.success,
                "content_hash": pc.content_hash,
                "version_detected": pc.version_detected,
                "last_modified": pc.last_modified,
                "error": pc.error,
                "timestamp": pc.timestamp,
            }

        for change in self.changes[-100:]:  # Keep last 100 changes
            data["changes"].append({
                "platform_id": change.platform_id,
                "url": change.url,
                "change_type": change.change_type,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "detected_at": change.detected_at,
            })

        self.cache_file.write_text(json.dumps(data, indent=2))

    def fetch_url(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch URL content using stdlib."""
        if not url:
            return None

        try:
            request = Request(url, headers={"User-Agent": self.USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode('utf-8', errors='ignore')
        except HTTPError as e:
            return None
        except URLError as e:
            return None
        except Exception as e:
            return None

    def compute_content_hash(self, content: str) -> str:
        """Compute hash of content, normalizing whitespace."""
        # Normalize content for stable hashing
        normalized = re.sub(r'\s+', ' ', content.strip())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def extract_version(self, content: str) -> Optional[str]:
        """Extract version number from page content."""
        for pattern in self.VERSION_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def check_url(self, url: str, platform_id: str) -> PageCheck:
        """Check a documentation URL for changes."""
        old_check = self.page_cache.get(url)

        content = self.fetch_url(url)

        if content is None:
            check = PageCheck(
                url=url,
                success=False,
                error="Failed to fetch URL",
            )
            self.page_cache[url] = check
            return check

        content_hash = self.compute_content_hash(content)
        version = self.extract_version(content)

        check = PageCheck(
            url=url,
            success=True,
            content_hash=content_hash,
            version_detected=version,
        )
        self.page_cache[url] = check

        # Detect changes
        if old_check and old_check.success:
            if old_check.content_hash != content_hash:
                self.changes.append(DocChange(
                    platform_id=platform_id,
                    url=url,
                    change_type="content",
                    old_value=old_check.content_hash,
                    new_value=content_hash,
                ))

            if old_check.version_detected and version:
                if old_check.version_detected != version:
                    self.changes.append(DocChange(
                        platform_id=platform_id,
                        url=url,
                        change_type="version",
                        old_value=old_check.version_detected,
                        new_value=version,
                    ))

        return check

    def check_all_platforms(self, registry) -> dict[str, PageCheck]:
        """Check documentation URLs for all platforms."""
        results = {}

        for pid, config in registry.all().items():
            if config.docs_url:
                results[pid] = self.check_url(config.docs_url, pid)

            if config.changelog_url:
                results[f"{pid}_changelog"] = self.check_url(config.changelog_url, pid)

        self.save_cache()
        return results

    def get_recent_changes(self, days: int = 7) -> list[DocChange]:
        """Get changes detected in the last N days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        recent = []
        for change in self.changes:
            try:
                change_time = datetime.fromisoformat(change.detected_at).timestamp()
                if change_time >= cutoff:
                    recent.append(change)
            except Exception:
                pass

        return recent

    def get_changes_by_platform(self, platform_id: str) -> list[DocChange]:
        """Get all changes for a specific platform."""
        return [c for c in self.changes if c.platform_id == platform_id]

    def check_for_breaking_changes(self, content: str) -> list[str]:
        """Scan content for indicators of breaking changes."""
        indicators = []

        breaking_patterns = [
            (r'breaking\s+change', "Breaking change mentioned"),
            (r'deprecated', "Deprecation notice"),
            (r'removed\s+support', "Feature removal"),
            (r'migration\s+required', "Migration required"),
            (r'incompatible', "Incompatibility warning"),
            (r'must\s+update', "Mandatory update"),
        ]

        content_lower = content.lower()
        for pattern, message in breaking_patterns:
            if re.search(pattern, content_lower):
                indicators.append(message)

        return indicators

    def generate_summary(self) -> dict:
        """Generate a summary of monitoring status."""
        total_pages = len(self.page_cache)
        successful = sum(1 for p in self.page_cache.values() if p.success)
        failed = total_pages - successful

        recent_changes = self.get_recent_changes(7)
        version_changes = [c for c in recent_changes if c.change_type == "version"]
        content_changes = [c for c in recent_changes if c.change_type == "content"]

        return {
            "total_monitored": total_pages,
            "successful_checks": successful,
            "failed_checks": failed,
            "changes_last_7_days": len(recent_changes),
            "version_changes": len(version_changes),
            "content_changes": len(content_changes),
            "platforms_with_changes": list(set(c.platform_id for c in recent_changes)),
        }
