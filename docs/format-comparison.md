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
license: Optional license info
---
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

### Context (`GEMINI.md`)
Hierarchical loading from home → project root → subdirectories.

```markdown
# Global Instructions

Your instructions here...
```

### Key Differences from Claude Code:
1. No separate "agents" concept - use skills instead
2. Skills directory is at `~/.gemini/skills/` (NOT antigravity/)
3. Global context file is `GEMINI.md` not `CLAUDE.md`
4. Context files load hierarchically (global → project → subdirs)

---

## Codex CLI (`~/.codex/`)

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
```

### Key Differences from Claude Code:
1. Single file instead of individual agent files
2. No YAML frontmatter
3. Uses TOML for configuration (not JSON)
4. No built-in skill system

---

## Conversion Matrix

| From | To | Strategy |
|------|-----|----------|
| Claude Agent → Gemini Skill | Strip tools/model/color, keep name/desc, create SKILL.md |
| Claude Agent → Codex | Aggregate all into single AGENTS.md, strip frontmatter |
| Claude Skill → Gemini Skill | Direct copy (compatible) |
| Claude Skill → Codex | Include in AGENTS.md as section |

## Sources

- [Gemini CLI Configuration](https://geminicli.com/docs/get-started/configuration/)
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/)
- [Codex CLI AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)
- [Codex CLI Configuration](https://github.com/openai/codex/blob/main/docs/config.md)
