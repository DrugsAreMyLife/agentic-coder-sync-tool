"""Utility modules for Agent Management Suite."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.relationships import RelationshipAnalyzer
from utils.suggestions import SuggestionEngine
from utils.formatters import format_tools_list, format_description, truncate

__all__ = [
    "RelationshipAnalyzer",
    "SuggestionEngine",
    "format_tools_list",
    "format_description",
    "truncate",
]


# Lazy imports for optional modules
def get_platform_registry():
    from utils.platform_registry import get_registry
    return get_registry()


def get_version_tracker():
    from utils.version_tracker import VersionTracker
    return VersionTracker()


def get_compat_validator():
    from utils.compat_validator import CompatibilityValidator
    return CompatibilityValidator()


def get_web_monitor():
    from utils.web_monitor import WebMonitor
    return WebMonitor()


def get_doc_updater():
    from utils.doc_updater import DocUpdater
    return DocUpdater()


def get_exclusion_manager():
    from utils.exclusion_manager import ExclusionManager
    return ExclusionManager()


def get_workflow_manager():
    from utils.workflow_manager import WorkflowManager
    return WorkflowManager()
