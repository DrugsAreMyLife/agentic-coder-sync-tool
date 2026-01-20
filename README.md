# Agentic Coder Sync Tool

Synchronize your AI coding agent configurations across multiple platforms. Keep your agents, skills, and instructions in sync between Claude Code, Gemini CLI, Antigravity, and Codex CLI.

## Why?

If you use multiple AI coding assistants, you've likely noticed they each have their own configuration formats:

- **Claude Code**: `~/.claude/agents/*.md` + `~/.claude/skills/*/SKILL.md`
- **Gemini CLI**: `~/.gemini/skills/*/SKILL.md` + `GEMINI.md`
- **Codex CLI**: `~/.codex/AGENTS.md`

This tool lets you maintain your agent definitions in Claude Code format and automatically sync them to all other platforms.

## Features

- **One-way sync**: Claude Code → Gemini CLI / Antigravity / Codex CLI
- **Bidirectional sync**: Also sync Gemini skills back to Claude
- **Format conversion**: Automatically converts between platform-specific formats
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

Copy to your Claude Code skills directory:

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

### Sync to All Platforms

```bash
python sync_agents.py --all
```

### Sync to Specific Platform

```bash
# Gemini CLI and Antigravity
python sync_agents.py --platform gemini

# Codex CLI
python sync_agents.py --platform codex
```

### Preview Changes (Dry Run)

```bash
python sync_agents.py --all --dry-run
```

### List Available Agents and Skills

```bash
python sync_agents.py --list
```

### Bidirectional Sync

Sync Gemini skills back to Claude:

```bash
python sync_agents.py --all --bidirectional
```

### Verbose Output

```bash
python sync_agents.py --all --verbose
```

## Supported Platforms

| Platform | Source | Target | Config Location |
|----------|--------|--------|-----------------|
| Claude Code | Read | - | `~/.claude/` |
| Gemini CLI | Read (bidirectional) | Write | `~/.gemini/` |
| Antigravity | - | Write | `~/.gemini/antigravity/` |
| Codex CLI | - | Write | `~/.codex/` |

## Directory Structure

```
~/.claude/
├── CLAUDE.md              # Global instructions (synced to all platforms)
├── agents/
│   └── my-agent.md        # Agent definitions
└── skills/
    └── my-skill/
        ├── SKILL.md       # Skill definition
        ├── scripts/       # Optional scripts
        └── references/    # Optional docs

~/.gemini/
├── GEMINI.md              # Generated from Claude config
├── skills/
│   ├── my-skill/          # Direct copy from Claude
│   └── _claude_agents/    # Agents converted to skills
│       └── my-agent/
│           └── SKILL.md
└── antigravity/
    └── skills/            # Same structure for Antigravity

~/.codex/
├── AGENTS.md              # Aggregated agent instructions
└── config.toml.suggested  # Suggested configuration
```

## Format Conversion

### Claude Agent → Gemini Skill

Claude agents are converted to Gemini skills:

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
description: Design RESTful APIs
---

# API Designer Agent

Instructions here...
```

### Claude Agents → Codex AGENTS.md

All Claude agents are aggregated into a single `AGENTS.md`:

```markdown
# Codex CLI Agent Instructions

## Global Instructions
(Contents of CLAUDE.md)

---

## Specialized Agent Instructions

### Api Designer

**Purpose**: Design RESTful APIs

# API Designer Agent

Instructions here...

---
```

## Requirements

- Python 3.9+
- No external dependencies (uses only standard library)

## Configuration

The sync script uses these default paths:

| Variable | Default | Description |
|----------|---------|-------------|
| Claude Dir | `~/.claude/` | Source for agents and skills |
| Gemini Dir | `~/.gemini/` | Target for Gemini CLI |
| Codex Dir | `~/.codex/` | Target for Codex CLI |

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
