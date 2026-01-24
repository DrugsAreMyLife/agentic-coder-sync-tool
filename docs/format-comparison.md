# AI CLI Platform Format Comparison

This reference documents the configuration formats for different AI CLI platforms to enable cross-platform agent synchronization.

## Claude Code (`~/.claude/`)

### Agents (`agents/*.md`)
Individual markdown files with YAML frontmatter.

```yaml
---
name: agent-name
description: What this agent does
tools: Read, Write, Edit, Bash
model: sonnet
color: "#2563EB"
---

# Agent Title

Agent instructions in markdown...
```

**Fields:**
- `name` (required): Identifier for the agent
- `description` (required): When to use this agent
- `tools` (required): Comma-separated list of available tools
- `model` (optional): sonnet, opus, haiku
- `color` (optional): Hex color for UI

### Skills (`skills/*/SKILL.md`)
Directory-based with SKILL.md and optional resources.

```
skill-name/
├── SKILL.md           # Required
├── scripts/           # Optional - executable code
├── references/        # Optional - documentation
└── assets/           # Optional - templates, images
```

**SKILL.md Frontmatter:**
```yaml
---
name: skill-name
description: What this skill provides
allowed-tools:
  - Read
  - Write
  - Bash
license: Optional license info
---
```

### Commands (`commands/*.md`)
Slash commands for quick access to workflows.

```yaml
---
description: Command description
argument-hint: Optional argument hint
allowed-tools: [Tool1, Tool2, Tool3]
---

# Command Instructions

What this command does...
```

### Hooks
**Location**: `~/.claude/settings.json` or `hooks/hooks.json` in plugins

**Hook Events:**
| Event | When it fires |
|-------|---------------|
| `SessionStart` | Session begins or resumes |
| `UserPromptSubmit` | User submits a prompt |
| `PreToolUse` | Before tool execution |
| `PermissionRequest` | When permission dialog appears |
| `PostToolUse` | After tool succeeds |
| `PostToolUseFailure` | After tool fails |
| `SubagentStart` | When spawning a subagent |
| `SubagentStop` | When subagent finishes |
| `Stop` | Claude finishes responding |
| `PreCompact` | Before context compaction |
| `SessionEnd` | Session terminates |
| `Notification` | Claude Code sends notifications |

**Configuration Format:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/validator.sh",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Plugins (`plugins/*/`)
Full plugin architecture for packaging and sharing.

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json        # Plugin manifest
├── commands/              # Slash commands
├── agents/               # Custom agents
├── skills/               # Skills
├── hooks/
│   └── hooks.json        # Hook definitions
└── .mcp.json             # MCP server config
```

**plugin.json:**
```json
{
  "name": "plugin-name",
  "description": "What the plugin does",
  "version": "1.0.0",
  "author": {
    "name": "Author Name"
  }
}
```

### MCP Servers (`.mcp.json`)
Model Context Protocol server configuration.

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["mcp-server/index.js"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    }
  }
}
```

---

## Gemini CLI (`~/.gemini/`)

### Skills (`skills/*/SKILL.md`)
**Format is identical to Claude Code skills!**

```
skill-name/
├── SKILL.md           # Required
├── scripts/           # Optional - executable files
├── references/        # Optional - static docs, schemas
└── assets/            # Optional - templates, binaries
```

### Discovery Locations (Precedence Order)
1. **Project Skills**: `.gemini/skills/`
2. **User Skills**: `~/.gemini/skills/`
3. **Extension Skills**: Bundled within extensions

### Enabling Skills
Add to `~/.gemini/settings.json`:
```json
{
  "experimental": {
    "skills": true
  }
}
```

### Extensions (`extensions/*/`)
Package prompts, MCP servers, skills, and commands.

```
extension-name/
├── gemini-extension.json  # Extension manifest
├── GEMINI.md              # Context file
├── skills/                # Extension skills
├── commands/              # TOML command files
└── hooks/
    └── hooks.json         # Hook definitions
```

**gemini-extension.json:**
```json
{
  "name": "extension-name",
  "version": "1.0.0",
  "description": "What the extension does",
  "contextFileName": "GEMINI.md",
  "excludeTools": ["Bash", "Edit", "Write"],
  "settings": [
    {
      "name": "API_KEY",
      "description": "API authentication key",
      "secret": true,
      "required": true
    }
  ],
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["${extensionPath}/mcp-server/index.js"]
    }
  }
}
```

### Commands (`commands/*.toml`)
TOML-based command definitions.

```toml
[command]
description = "Command description"
argument_hint = "optional"

[prompt]
content = """
Your command instructions here...
"""
```

### Context (`GEMINI.md`)
Hierarchical loading from home → project root → subdirectories.

```markdown
# Global Instructions

Your instructions here...
```

### Hooks (`hooks/hooks.json`)
Same format as Claude Code hooks within extensions.

### Key Differences from Claude Code
1. No separate "agents" concept - use skills instead
2. Skills directory is at `~/.gemini/skills/` (NOT antigravity/)
3. Global context file is `GEMINI.md` not `CLAUDE.md`
4. Context files load hierarchically (global → project → subdirs)
5. Uses `excludeTools` (blacklist) instead of `allowed-tools` (whitelist)
6. MCP paths use `${extensionPath}` variable substitution

---

## Antigravity (`~/.gemini/antigravity/`)

Antigravity is a specialized variant of Gemini CLI for browser automation and agent workflows.

### Skills (`skills/*/SKILL.md`)
**Same format as Gemini CLI skills.**

```
~/.gemini/antigravity/skills/
├── skill-name/
│   ├── SKILL.md
│   ├── scripts/
│   ├── references/
│   └── assets/
```

### Discovery Locations
1. **Global Scope**: `~/.gemini/antigravity/skills/`
2. **Workspace Scope**: `.agent/skills/`

### Key Differences from Gemini CLI
1. Located in `antigravity/` subdirectory within `.gemini/`
2. Specialized for agent workflows and browser automation
3. Same skill format, different discovery locations

---

## Codex CLI (`~/.codex/`)

### Skills (`skills/*/SKILL.md`)
**Format is identical to Claude Code, Gemini CLI, and Antigravity!**

```
skill-name/
├── SKILL.md           # Required
├── scripts/           # Optional - executable files
├── references/        # Optional - static docs, schemas
└── assets/            # Optional - templates, binaries
```

**Discovery Location:** `~/.codex/skills/`

### Skill Location Hierarchy (Precedence Order)
| Scope | Path | Use Case |
|-------|------|----------|
| REPO (current) | `$CWD/.codex/skills` | Folder-specific |
| REPO (parent) | `$CWD/../.codex/skills` | Nested repos |
| REPO (root) | `$REPO_ROOT/.codex/skills` | Repository-wide |
| USER | `~/.codex/skills` | Personal, cross-project |
| ADMIN | `/etc/codex/skills` | System-wide defaults |
| SYSTEM | Bundled | Built-in skills |

### Enabling Skills
```bash
codex --enable skills
```

### Instructions (`AGENTS.md`)
Single aggregated markdown file (no frontmatter).

```markdown
# Agent Instructions

## Section 1
Instructions...

## Section 2
More instructions...
```

**Discovery Order:**
1. `~/.codex/AGENTS.override.md` (if exists)
2. `~/.codex/AGENTS.md`
3. Project-level `AGENTS.md` files

### Configuration (`config.toml`)
```toml
model = "o4-mini"
approval_mode = "suggest"
project_doc_fallback_filenames = ["AGENTS.md", "CLAUDE.md"]

[features]
shell_snapshot = true
web_search_request = true
```

### Rules (`rules/*.rules`)
Command approval patterns.

```
prefix_rule(pattern=["python3", "/path/to/script.py"], decision="allow")
```

### Key Differences from Claude Code
1. Single AGENTS.md file instead of individual agent files
2. No YAML frontmatter in AGENTS.md
3. Uses TOML for configuration (not JSON)
4. Skills use identical format to Claude Code and Gemini CLI
5. No hooks system (uses rules instead)
6. No plugins/extensions system

---

## Tool Restriction Conversion

### Claude Code → Gemini CLI (Whitelist → Blacklist)
- Analyze `allowed-tools` list
- Generate `excludeTools` for all tools NOT in the list
- Special handling for wildcard permissions

**Example:**
```yaml
# Claude (allowed-tools)
allowed-tools: [Read, Write, Bash]
```
```json
// Gemini (excludeTools)
"excludeTools": ["Edit", "Glob", "Grep", "Task", "WebFetch", "WebSearch", ...]
```

### Gemini CLI → Claude Code (Blacklist → Whitelist)
- List all available tools
- Remove excluded tools
- Generate `allowed-tools` list

**Example:**
```json
// Gemini (excludeTools)
"excludeTools": ["Bash", "Edit", "Write"]
```
```yaml
# Claude (allowed-tools)
allowed-tools: [Read, Glob, Grep, Task, WebFetch, WebSearch, ...]
```

---

## MCP Path Transformation

### Claude Code → Gemini CLI
```json
// Claude (relative paths)
"args": ["mcp-server/index.js"]

// Gemini (with ${extensionPath})
"args": ["${extensionPath}/mcp-server/index.js"]
```

### Gemini CLI → Claude Code
```json
// Gemini (with variable)
"args": ["${extensionPath}/mcp-server/index.js"]

// Claude (relative paths)
"args": ["mcp-server/index.js"]
```

---

## Settings/Environment Variable Conversion

### Claude Code → Gemini CLI
Environment variables become settings schema:

```json
// Claude MCP env
"env": { "API_KEY": "${API_KEY}", "API_URL": "https://api.example.com" }

// Gemini settings
"settings": [
  { "name": "API_KEY", "description": "Api Key configuration", "secret": true, "required": true },
  { "name": "API_URL", "description": "Api Url configuration", "default": "https://api.example.com" }
]
```

### Gemini CLI → Claude Code
Settings become environment variable documentation:

```markdown
## Configuration

This skill requires the following environment variables:

- `API_KEY`: Api Key configuration **(required)** (secret)
- `API_URL`: Api Url configuration (default: https://api.example.com)
```

---

## Conversion Matrix

| From | To | Strategy |
|------|-----|----------|
| Claude Agent → Gemini Skill | Strip tools/model/color, keep name/desc, create SKILL.md |
| Claude Agent → Antigravity Skill | Strip tools/model/color, keep name/desc, create SKILL.md |
| Claude Agent → Codex Skill | Strip tools/model/color, keep name/desc, create SKILL.md |
| Claude Agent → Codex AGENTS.md | Aggregate all into single AGENTS.md, strip frontmatter |
| Claude Skill → Gemini Skill | Direct copy (compatible format) |
| Claude Skill → Antigravity Skill | Direct copy (compatible format) |
| Claude Skill → Codex Skill | Direct copy (compatible format) |
| Claude Command → Gemini Command | Markdown to TOML conversion |
| Claude Hook → Gemini Hook | Format preserved (JSON hooks.json) |
| Claude Plugin → Gemini Extension | Manifest conversion, path transformation |
| Gemini Skill → Claude Skill | Direct copy (compatible format) |
| Gemini Extension → Claude Plugin | Manifest conversion, settings to env docs |
| Codex Skill → Claude Skill | Direct copy (compatible format) |

## Sources

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Claude Code Plugins](https://code.claude.com/docs/en/plugins)
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/)
- [Gemini CLI Extensions](https://geminicli.com/docs/extensions/)
- [Codex CLI Skills](https://developers.openai.com/codex/skills/)
- [Codex CLI Configuration](https://github.com/openai/codex/blob/main/docs/config.md)
- [Antigravity Skills](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)
- [skill-porter](https://github.com/jduncan-rva/skill-porter) - Cross-platform conversion patterns
