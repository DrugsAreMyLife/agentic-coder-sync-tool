# Agent Management & Sync Suite

A comprehensive CLI tool for managing and synchronizing Claude Code agents, skills, plugins, commands, and hooks across **14+ AI coding platforms**. Features an interactive menu system with colorful output, agent relationship visualization, and platform sync management.

## Quick Start

```bash
cd src
python3 sync_agents.py        # Launch interactive menu
python3 sync_agents.py --all  # Sync to all platforms
```

## Interactive Menu

Run without arguments for the full interactive experience:

```
+---------------------------------------------------------+
|  AGENT MANAGEMENT & SYNC SUITE                          |
+---------------------------------------------------------+

  26 agents | 23 skills | 2 plugins

  [1] Agent Manager
  [2] Skill Browser & Builder
  [3] Plugin Browser & Builder
  [4] Command Browser & Builder
  [5] Hook Browser & Builder
  [6] Sync to Platforms
  [7] Platform Status
  [8] Exit

>
```

### Features
- **Agent Manager** - Browse agents with hierarchy visualization and relationship graphs
- **Skill Browser** - Create, edit, categorize, and sync skills
- **Plugin Browser** - Explore installed plugins with component breakdown
- **Command Browser** - View and create slash commands
- **Hook Browser** - Manage event hooks with enable/disable
- **Platform Sync** - One-click export to 12+ AI coding platforms

## Why?

If you use multiple AI coding assistants, you've likely noticed they each have their own configuration formats:

- **Claude Code**: `~/.claude/skills/*/SKILL.md` + `~/.claude/agents/*.md` + plugins
- **Gemini CLI**: `~/.gemini/skills/*/SKILL.md` + `~/.gemini/extensions/`
- **Antigravity**: `~/.gemini/antigravity/skills/*/SKILL.md`
- **Codex CLI**: `~/.codex/skills/*/SKILL.md` + `~/.codex/AGENTS.md`

This tool lets you maintain your agent definitions in any platform and automatically sync them to all others.

## Features

- **Bidirectional sync**: Claude Code ↔ Gemini CLI ↔ Codex CLI
- **Full component support**: Agents, Skills, Commands, Hooks, Plugins, MCP Servers
- **Format conversion**: Automatically converts between platform-specific formats
- **Tool restriction conversion**: `allowed-tools` (whitelist) ↔ `excludeTools` (blacklist)
- **MCP path transformation**: Handles `${extensionPath}` vs relative paths
- **Settings inference**: Converts environment variables to settings schema
- **Dry run mode**: Preview changes before applying
- **Incremental updates**: Track sync state for efficient updates

## Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/DrugsAreMyLife/agentic-coder-sync-tool.git

# Run the sync script
python agentic-coder-sync-tool/src/sync_agents.py --all
```

### As a Claude Code Skill

```bash
mkdir -p ~/.claude/skills/agent-sync
cp -r agentic-coder-sync-tool/src/* ~/.claude/skills/agent-sync/scripts/
cp agentic-coder-sync-tool/docs/format-comparison.md ~/.claude/skills/agent-sync/references/
```

Create `~/.claude/skills/agent-sync/SKILL.md`:

```markdown
---
name: agent-sync
description: Synchronizes Claude Code agents and skills to Gemini CLI, Antigravity, and Codex CLI.
---

# Agent Sync

Sync your agents across platforms.

## Usage

python "${SKILL_DIR}/scripts/sync_agents.py" --all
```

## Usage

### Interactive Mode (Recommended)

```bash
cd src
python sync_agents.py           # Full interactive menu
python sync_agents.py -i        # Force interactive mode
```

### Command Line Mode

```bash
# Sync to all platforms
python sync_agents.py --all

# Sync to specific platform
python sync_agents.py --platform gemini
python sync_agents.py --platform codex
python sync_agents.py --platform cursor

# Preview changes without applying
python sync_agents.py --all --dry-run

# List all components
python sync_agents.py --list

# Verbose output
python sync_agents.py --all --verbose
```

### Available Flags

| Flag | Description |
|------|-------------|
| (none) | Launch interactive menu |
| `--all, -a` | Sync to all platforms |
| `--platform, -p` | Sync to specific platform |
| `--list, -l` | List all components |
| `--dry-run, -n` | Preview changes |
| `--verbose, -v` | Verbose output |
| `--interactive, -i` | Force interactive mode |

## Supported Platforms

### SKILL.md Format (Direct Copy Compatible)

| Platform | Skills Location | Config Location | Notes |
|----------|-----------------|-----------------|-------|
| Claude Code | `~/.claude/skills/` | `~/.claude/` | Full feature support (source of truth) |
| Codex CLI | `~/.codex/skills/` | `~/.codex/` | SKILL.md + AGENTS.md |
| Gemini CLI | `~/.gemini/skills/` | `~/.gemini/` | Requires `experimental.skills` enabled |
| Antigravity | `~/.gemini/antigravity/skills/` | `~/.gemini/antigravity/` | Uses Gemini skill format |
| Continue | `~/.continue/skills/` | `~/.continue/` | IDE extension |
| OpenCode | `~/.opencode/skills/` | `~/.opencode/` | Claude-compatible |
| Trae | `~/.trae/skills/` | `~/.trae/` | Claude-compatible |

### Other Formats (Conversion Required)

| Platform | Format | Location | Notes |
|----------|--------|----------|-------|
| Cursor | `.cursorrules`, `.mdc` files | `.cursor/rules/` | Project rules, no global |
| Windsurf | Workflows in memories | `.windsurf/workflows/` | Markdown workflows |
| Roo Code | `.roorules`, modes | `.roo/` | Custom modes per task |
| Kiro | Steering files | `.kiro/steering/` | AWS-backed, hooks support |
| GitHub Copilot | `.prompt.md` files | `.github/prompts/` | Project-level only |
| Aider | CONVENTIONS.md | Project root | Single file format |
| Agent Zero | Prompts + instruments | `prompts/`, `python/tools/` | Custom agent framework |

## What Gets Synced

### Component Support Matrix

| Component | Claude Code | Gemini CLI | Antigravity | Codex CLI |
|-----------|-------------|------------|-------------|-----------|
| Skills | Native | Native | Native | Native |
| Agents | Native | → Skills | → Skills | → AGENTS.md |
| Commands | Native (`commands/`) | → TOML commands | - | - |
| Hooks | Full support | `hooks.json` | - | - |
| Plugins | Native | → Extensions | - | - |
| MCP Servers | `.mcp.json` | Extension manifest | - | - |

### Format Conversions

**Tool Restrictions (Claude ↔ Gemini)**
- Claude uses `allowed-tools` (whitelist - only listed tools permitted)
- Gemini uses `excludeTools` (blacklist - listed tools blocked)
- Automatic conversion with logic inversion

**MCP Server Paths**
- Claude: Relative paths from skill directory
- Gemini: Uses `${extensionPath}` variable substitution
- Automatic path transformation during sync

**Settings/Environment Variables**
- Claude: Environment variables for configuration
- Gemini: Settings schema with prompts during installation
- Automatic inference and documentation generation

## Directory Structure

```
~/.claude/
├── CLAUDE.md              # Global instructions (synced to all platforms)
├── agents/
│   └── my-agent.md        # Agent definitions
├── skills/
│   └── my-skill/
│       ├── SKILL.md       # Skill definition
│       ├── scripts/       # Optional scripts
│       └── references/    # Optional docs
├── commands/
│   └── my-command.md      # Slash commands
├── hooks/
│   └── my-hook.sh         # Hook scripts
├── plugins/
│   └── my-plugin/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/
│       ├── agents/
│       ├── skills/
│       └── hooks/
├── settings.json          # Hooks configuration
└── .mcp.json              # MCP server configuration

~/.gemini/
├── GEMINI.md              # Generated from Claude config
├── skills/
│   ├── my-skill/          # Direct copy from Claude
│   └── _claude_agents/    # Agents converted to skills
│       └── my-agent/
│           └── SKILL.md
├── extensions/
│   └── claude-sync/       # Auto-generated extension
│       ├── gemini-extension.json
│       ├── hooks/
│       │   └── hooks.json
│       └── commands/
│           └── my-command.toml
├── settings.json          # Enable experimental.skills here
└── antigravity/
    └── skills/            # Same structure for Antigravity

~/.codex/
├── AGENTS.md              # Aggregated agent instructions
├── config.toml.suggested  # Suggested configuration
└── skills/                # Skill directories (same format as Gemini)
    ├── my-skill/
    │   └── SKILL.md
    └── _claude_agents/    # Agents converted to skills
        └── my-agent/
            └── SKILL.md
```

## Format Conversion Examples

### Claude Agent → Gemini Skill

**Input** (`~/.claude/agents/api-designer.md`):
```yaml
---
name: api-designer
description: Design RESTful APIs
tools: Read, Write, Edit
model: sonnet
color: "#2563EB"
---

# API Designer Agent

Instructions here...
```

**Output** (`~/.gemini/skills/_claude_agents/api-designer/SKILL.md`):
```yaml
---
name: api-designer
description: "Design RESTful APIs"
---

# API Designer Agent

Instructions here...
```

### Claude Skill with Tool Restrictions → Gemini Extension

**Input** (`~/.claude/skills/code-formatter/SKILL.md`):
```yaml
---
name: code-formatter
description: Format code files
allowed-tools:
  - Read
  - Write
  - Bash
---
```

**Output** (`~/.gemini/extensions/claude-sync/gemini-extension.json`):
```json
{
  "name": "claude-sync",
  "excludeTools": ["Edit", "Glob", "Grep", "Task", "WebFetch", "..."]
}
```

### MCP Server Path Transformation

**Claude format:**
```json
{
  "args": ["mcp-server/index.js"]
}
```

**Gemini format:**
```json
{
  "args": ["${extensionPath}/mcp-server/index.js"]
}
```

## Enabling Skills in Gemini CLI

Skills require experimental features enabled. Add to `~/.gemini/settings.json`:

```json
{
  "experimental": {
    "skills": true
  }
}
```

## Requirements

- Python 3.9+
- No external dependencies (uses only standard library)

## Configuration

The sync script uses these default paths:

| Variable | Default | Description |
|----------|---------|-------------|
| Claude Dir | `~/.claude/` | Source for agents and skills |
| Claude Skills | `~/.claude/skills/` | Claude Code skill directories |
| Claude Commands | `~/.claude/commands/` | Claude Code slash commands |
| Claude Hooks | `~/.claude/hooks/` | Claude Code hook scripts |
| Claude Plugins | `~/.claude/plugins/` | Claude Code plugins |
| Gemini Dir | `~/.gemini/` | Target for Gemini CLI |
| Gemini Skills | `~/.gemini/skills/` | Gemini CLI skill directories |
| Gemini Extensions | `~/.gemini/extensions/` | Gemini CLI extensions |
| Antigravity Skills | `~/.gemini/antigravity/skills/` | Antigravity skill directories |
| Codex Dir | `~/.codex/` | Target for Codex CLI |
| Codex Skills | `~/.codex/skills/` | Codex CLI skill directories |

## Comparison with skill-porter

This tool was inspired by [skill-porter](https://github.com/jduncan-rva/skill-porter) and incorporates similar patterns:

| Feature | agentic-coder-sync-tool | skill-porter |
|---------|------------------------|--------------|
| Language | Python | Node.js |
| Scope | Full config sync | Skill conversion |
| Bidirectional | Yes | Yes |
| Tool restriction conversion | Yes | Yes |
| MCP path transformation | Yes | Yes |
| Settings inference | Yes | Yes |
| Hooks sync | Yes | No |
| Commands sync | Yes | No |
| Plugins sync | Yes | No |
| Agents → Skills | Yes | No |
| AGENTS.md generation | Yes | No |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [Claude Code](https://claude.ai/code) - Anthropic's CLI for Claude
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) - Google's CLI for Gemini
- [Codex CLI](https://github.com/openai/codex) - OpenAI's coding agent CLI
- [skill-porter](https://github.com/jduncan-rva/skill-porter) - Cross-platform skill converter

## Maintenance & Updates

### Verify Platform Status

Run the verification script to check all platform installations:

```bash
python scripts/verify_platforms.py
```

Export results to JSON:

```bash
python scripts/verify_platforms.py --json report.json
```

### Research Process

See [docs/RESEARCH_PROCESS.md](docs/RESEARCH_PROCESS.md) for:
- How to research new AI coding platforms
- Template for adding platform support
- Quarterly maintenance checklist
- Web search queries for documentation updates

### Platform Feature Matrix

See [docs/platform-feature-matrix.md](docs/platform-feature-matrix.md) for detailed compatibility information.

## Sources

Documentation used to build this tool:

**Primary Platforms:**
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Codex CLI](https://github.com/openai/codex)
- [Gemini CLI](https://googlegemini.github.io/gemini-cli/docs/)

**IDE Extensions:**
- [Cursor Docs](https://docs.cursor.com/)
- [Windsurf Docs](https://docs.windsurf.com/)
- [Roo Code Docs](https://docs.roocode.com/)
- [Continue Docs](https://docs.continue.dev/)
- [GitHub Copilot Docs](https://docs.github.com/en/copilot)

**Other Tools:**
- [Kiro Docs](https://kiro.dev/docs/)
- [Aider Docs](https://aider.chat/docs/)
- [Agent Zero](https://github.com/frdel/agent-zero)
