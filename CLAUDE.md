# Agent Management & Sync Suite

## Project Overview

This is a comprehensive CLI tool for managing and synchronizing Claude Code agents, skills, plugins, commands, and hooks across multiple AI coding agent platforms.

## Architecture

```
src/
├── sync_agents.py           # Main sync logic and CLI entry point
├── menu/                    # Interactive menu system
│   ├── __init__.py
│   ├── colors.py            # ANSI color definitions (no emojis)
│   ├── base.py              # Base menu class
│   ├── main_menu.py         # Main menu screen
│   ├── agent_manager.py     # Agent browser/editor with relationships
│   ├── skill_browser.py     # Skill browser/builder
│   ├── plugin_browser.py    # Plugin browser
│   ├── command_browser.py   # Command browser/builder
│   ├── hook_browser.py      # Hook browser/builder
│   ├── sync_menu.py         # Platform sync menu
│   ├── compat_menu.py       # Compatibility check menu
│   ├── exclusion_menu.py    # Exclusion manager menu
│   └── workflow_menu.py     # Workflow designer menu
└── utils/
    ├── __init__.py
    ├── relationships.py     # Agent relationship analysis
    ├── suggestions.py       # Integration suggestions engine
    ├── formatters.py        # Output formatting utilities
    ├── platform_registry.py # Consolidated platform metadata
    ├── version_tracker.py   # Platform version tracking
    ├── compat_validator.py  # Sync validation and backups
    ├── web_monitor.py       # Documentation monitoring
    ├── doc_updater.py       # Auto-update documentation
    ├── exclusion_manager.py # Private component exclusions
    └── workflow_manager.py  # Agent workflow orchestration
```

## Key Features

1. **Interactive Menu System** - No arguments launches full interactive menu
2. **Agent Manager** - Browse agents with hierarchy visualization and relationship graphs
3. **Skill Browser & Builder** - Create, edit, and sync skills across platforms
4. **Plugin Browser** - Explore installed plugins with component breakdown
5. **Command Browser** - View and create slash commands
6. **Hook Browser** - Manage event hooks with enable/disable
7. **Platform Sync** - Export to 12+ AI coding platforms
8. **Workflow Designer** - Design agent handoff workflows with verbal commands
9. **Exclusion Manager** - Mark components as private/excluded from sync/export
10. **Compatibility Checker** - Validate platform compatibility and track changes

## Supported Platforms

### SKILL.md Compatible (direct copy)
- Codex CLI, Gemini CLI, Antigravity, Continue, OpenCode, Trae

### Requires Conversion
- Cursor, Windsurf, Roo Code, Kiro, GitHub Copilot, Aider

## Development Guidelines

### Style
- NO emojis in output - use ANSI colors and ASCII box drawing
- Use `[+]` for success, `[-]` for error, `[*]` for info
- Use `subprocess.run()` for shell commands (security best practice)

### Running
```bash
cd src
python3 sync_agents.py              # Interactive menu
python3 sync_agents.py --list       # List components
python3 sync_agents.py --all        # Sync to all platforms
python3 sync_agents.py --export     # Export to portable bundle
python3 sync_agents.py --import X   # Import from bundle
python3 sync_agents.py --help       # Show help
```

### Adding New Features
1. New menu screens go in `src/menu/` extending `BaseMenu`
2. Utility functions go in `src/utils/`
3. Platform sync methods go in `AgentSync` class in `sync_agents.py`

### Testing Changes
```bash
python3 -c "from sync_agents import AgentSync; s = AgentSync(); s.load_all_claude(); print('OK')"
python3 sync_agents.py --list
python3 sync_agents.py --dry-run --all
```

## Data Classes

- `AgentInfo` - Agent with name, description, tools, model, content
- `SkillInfo` - Skill with name, description, content, file structure
- `CommandInfo` - Slash command with allowed tools
- `HookInfo` - Event hook with matcher and command
- `PluginInfo` - Plugin with component flags

## Agent Relationship Analysis

The `RelationshipAnalyzer` class in `utils/relationships.py`:
- Calculates agent depth (0=orchestrator, 3=leaf specialist)
- Parses content for explicit agent references
- Infers parent/child/sibling relationships
- Generates ASCII relationship graphs

## Suggestion Engine

The `SuggestionEngine` class in `utils/suggestions.py`:
- Agent-specific suggestions (python-dev -> pytest, pre-commit)
- Tool-based suggestions (Bash -> safety-net)
- Category-based suggestions from description keywords

## Compatibility Checker

The compatibility system validates sync operations and tracks platform changes:

```bash
python3 sync_agents.py --compat check        # Quick status check
python3 sync_agents.py --compat validate     # Full sync validation
python3 sync_agents.py --compat monitor      # Check docs for changes
python3 sync_agents.py --compat update-docs  # Regenerate feature matrix
```

Components:
- `PlatformRegistry` - Single source of truth for all platform metadata
- `VersionTracker` - Tracks versions and generates alerts for changes
- `CompatibilityValidator` - Dry-run validation and backup/restore
- `WebMonitor` - Monitors platform docs for updates
- `DocUpdater` - Auto-updates platform-feature-matrix.md

## Exclusion Manager

Mark components as private/excluded from sync and export:

Configuration file: `~/.claude/.sync_exclusions.json`

Default patterns:
- `*-private` - Components ending with -private
- `*-local` - Components ending with -local
- `my-*` - Personal agents starting with my-

## Workflow Designer

Design agent handoff workflows for complex multi-agent tasks:

Configuration directory: `~/.claude/workflows/`

Verbal command patterns for runtime agent redirection:
- "hand off to <agent>" - Transfer to another agent
- "switch to <agent>" - Change active agent
- "delegate to <agent>" - Let agent take over
- "pause workflow" / "resume workflow" - Flow control

Built-in workflows:
- `code-review` - Multi-agent code review
- `feature-dev` - Guided feature development
