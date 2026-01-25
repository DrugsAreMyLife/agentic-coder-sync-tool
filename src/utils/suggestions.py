"""Integration suggestion engine for agents."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Suggestion:
    """A suggested integration for an agent."""
    target: str  # What to integrate with
    reason: str  # Why this integration helps
    category: str  # skill, hook, mcp, agent


class SuggestionEngine:
    """
    Hybrid suggestion engine that generates integration suggestions
    based on agent capabilities and common patterns.
    """

    # Agent-specific suggestions
    AGENT_SUGGESTIONS = {
        "python-dev": [
            Suggestion("pytest-runner", "Automated testing with pytest", "skill"),
            Suggestion("pre-commit", "Pre-commit hooks for linting", "hook"),
            Suggestion("db-engineer", "SQLAlchemy/database integration", "agent"),
            Suggestion("docker-deploy", "Container deployment", "skill"),
            Suggestion("poetry-mcp", "Poetry package management", "mcp"),
        ],
        "typescript-dev": [
            Suggestion("jest-runner", "Automated testing with Jest", "skill"),
            Suggestion("eslint-hook", "ESLint validation on save", "hook"),
            Suggestion("frontend-design", "UI/UX design integration", "skill"),
            Suggestion("npm-mcp", "NPM package management", "mcp"),
        ],
        "rust-dev": [
            Suggestion("cargo-test", "Automated testing with Cargo", "skill"),
            Suggestion("clippy-hook", "Clippy linting on save", "hook"),
            Suggestion("crates-mcp", "Crates.io integration", "mcp"),
        ],
        "go-dev": [
            Suggestion("go-test", "Automated testing with go test", "skill"),
            Suggestion("golint-hook", "Go linting on save", "hook"),
            Suggestion("go-modules-mcp", "Go modules management", "mcp"),
        ],
        "test-engineer": [
            Suggestion("coverage-report", "Test coverage reporting", "skill"),
            Suggestion("ci-integration", "CI/CD pipeline integration", "hook"),
            Suggestion("fixtures-mcp", "Test fixture management", "mcp"),
        ],
        "security-reviewer": [
            Suggestion("owasp-scanner", "OWASP vulnerability scanning", "skill"),
            Suggestion("secret-scanner-hook", "Secret detection on commit", "hook"),
            Suggestion("cve-mcp", "CVE database integration", "mcp"),
        ],
        "db-engineer": [
            Suggestion("migration-tool", "Database migration management", "skill"),
            Suggestion("schema-validation", "Schema validation on change", "hook"),
            Suggestion("sql-mcp", "SQL query assistance", "mcp"),
        ],
        "devops-engineer": [
            Suggestion("terraform-validate", "Terraform validation", "skill"),
            Suggestion("k8s-lint", "Kubernetes manifest linting", "hook"),
            Suggestion("aws-mcp", "AWS service integration", "mcp"),
        ],
        "doc-curator": [
            Suggestion("markdown-lint", "Markdown linting", "skill"),
            Suggestion("link-checker", "Broken link detection", "hook"),
            Suggestion("docs-mcp", "Documentation site integration", "mcp"),
        ],
    }

    # Tool-based suggestions (apply when agent has specific tools)
    TOOL_SUGGESTIONS = {
        "Bash": [
            Suggestion("safety-net", "Add guardrails for shell commands", "skill"),
            Suggestion("command-audit", "Log and audit shell commands", "hook"),
        ],
        "Write": [
            Suggestion("pre-commit", "Validate changes before commit", "hook"),
            Suggestion("format-on-save", "Auto-format on file save", "hook"),
        ],
        "Edit": [
            Suggestion("backup-hook", "Backup files before editing", "hook"),
        ],
        "WebFetch": [
            Suggestion("cache-mcp", "Response caching for performance", "mcp"),
            Suggestion("rate-limiter", "API rate limiting", "hook"),
        ],
        "Task": [
            Suggestion("task-monitor", "Monitor spawned agent performance", "skill"),
            Suggestion("context-consolidator", "Prevent context bloat", "agent"),
        ],
    }

    # Category-based suggestions (apply based on description keywords)
    CATEGORY_SUGGESTIONS = {
        "frontend": [
            Suggestion("storybook", "Component documentation", "skill"),
            Suggestion("lighthouse", "Performance auditing", "skill"),
        ],
        "backend": [
            Suggestion("api-docs", "OpenAPI documentation", "skill"),
            Suggestion("load-test", "Load testing integration", "skill"),
        ],
        "database": [
            Suggestion("query-analyzer", "Query performance analysis", "skill"),
            Suggestion("backup-scheduler", "Automated backup scheduling", "hook"),
        ],
        "security": [
            Suggestion("pen-test", "Penetration testing tools", "skill"),
            Suggestion("audit-log", "Security audit logging", "hook"),
        ],
        "deploy": [
            Suggestion("rollback-hook", "Automatic rollback on failure", "hook"),
            Suggestion("health-check", "Deployment health monitoring", "skill"),
        ],
    }

    def __init__(self):
        pass

    def suggest(self, agent, max_suggestions: int = 5) -> list[Suggestion]:
        """Generate integration suggestions for an agent."""
        suggestions = []
        seen_targets = set()

        # 1. Agent-specific suggestions
        if agent.name in self.AGENT_SUGGESTIONS:
            for s in self.AGENT_SUGGESTIONS[agent.name]:
                if s.target not in seen_targets:
                    suggestions.append(s)
                    seen_targets.add(s.target)

        # 2. Tool-based suggestions
        for tool in agent.tools:
            if tool in self.TOOL_SUGGESTIONS:
                for s in self.TOOL_SUGGESTIONS[tool]:
                    if s.target not in seen_targets:
                        suggestions.append(s)
                        seen_targets.add(s.target)

        # 3. Category-based suggestions (from description)
        description = str(agent.description).lower()
        for category, cat_suggestions in self.CATEGORY_SUGGESTIONS.items():
            if category in description or category in agent.name:
                for s in cat_suggestions:
                    if s.target not in seen_targets:
                        suggestions.append(s)
                        seen_targets.add(s.target)

        # 4. Universal suggestions for certain tool combinations
        if "Bash" in agent.tools and "Write" in agent.tools:
            s = Suggestion("file-watcher", "Watch for file changes and trigger actions", "skill")
            if s.target not in seen_targets:
                suggestions.append(s)

        # Sort by relevance (agent-specific first, then tools, then categories)
        return suggestions[:max_suggestions]

    def format_suggestions(self, suggestions: list[Suggestion]) -> list[str]:
        """Format suggestions as display strings."""
        result = []
        for i, s in enumerate(suggestions, 1):
            category_icon = {
                "skill": "S",
                "hook": "H",
                "mcp": "M",
                "agent": "A",
            }.get(s.category, "?")
            result.append(f"{i}. [{category_icon}] Connect to {s.target}")
            result.append(f"      {s.reason}")
        return result

    def get_suggestion_by_index(self, suggestions: list[Suggestion], index: int) -> Optional[Suggestion]:
        """Get a suggestion by its 1-based index."""
        if 1 <= index <= len(suggestions):
            return suggestions[index - 1]
        return None
