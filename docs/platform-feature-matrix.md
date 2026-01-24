# AI Coding Agent Platform Feature Matrix

A comprehensive comparison of features across AI coding agent platforms. This document maps analogous features to Claude Code's architecture (Skills, Commands, Hooks, Plugins, MCP Servers).

> **Legend**: ✅ Supported | ⚠️ Partial/Different | ❌ Not Supported | ❓ Unknown/Needs Research

---

## SKILLS

Directory-based reusable instruction sets that provide domain-specific knowledge and capabilities.

| Platform | Company | Skill Location | Skill Filename | Format | Notes |
|----------|---------|----------------|----------------|--------|-------|
| **Claude Code** | Anthropic | `~/.claude/skills/` | `SKILL.md` | YAML frontmatter + MD | Native, full support |
| **Codex CLI** | OpenAI | `~/.codex/skills/` | `SKILL.md` | YAML frontmatter + MD | Same format as Claude |
| **Gemini CLI** | Google | `~/.gemini/skills/` | `SKILL.md` | YAML frontmatter + MD | Requires `experimental.skills` enabled |
| **Antigravity** | Google | `~/.gemini/antigravity/skills/` | `SKILL.md` | YAML frontmatter + MD | Same format as Gemini |
| **OpenCode** | SST | `~/.opencode/skills/` | `SKILL.md` | YAML frontmatter + MD | Also reads Claude/Codex skill dirs |
| **Trae** | ByteDance | `.trae/skills/` | `SKILL.md` | YAML frontmatter + MD | Same format as Claude |
| **Continue** | Continue.dev | `.continue/skills/` | `SKILL.md` | YAML frontmatter + MD | Compatible with Claude format |
| **Cursor** | Anysphere | `.cursor/commands/` | `*.md` | Plain MD | Called "commands", not skills |
| **Windsurf** | Codeium | `.windsurf/workflows/` | `*.md` | Plain MD | Called "workflows" |
| **Roo Code** | RooCodeInc | `.roo/commands/` | `*.md` | Plain MD | Also has `.roo/rules/` |
| **Kiro** | AWS | `.kiro/steering/` | `*.md` | Plain MD | Called "steering files" |
| **GitHub Copilot** | Microsoft | `.github/prompts/` | `*.prompt.md` | Plain MD | Called "prompts" |
| **Aider** | Aider-AI | Project root | `CONVENTIONS.md` | Plain MD | Single file conventions |
| **Agent Zero** | agent0ai | `prompts/` | `*.md` | Plain MD | Prompt-based architecture |
| **Qoder** | Alibaba | Via Memory settings | N/A | Plain-text rules | In-app configuration |

### Skill Directory Subdirectories

| Platform | `scripts/` | `references/` | `assets/` |
|----------|:----------:|:-------------:|:---------:|
| Claude Code | ✅ | ✅ | ✅ |
| Codex CLI | ✅ | ✅ | ✅ |
| Gemini CLI | ✅ | ✅ | ✅ |
| Antigravity | ✅ | ✅ | ✅ |
| OpenCode | ✅ | ✅ | ✅ |
| Trae | ✅ | ✅ | ✅ |
| Continue | ❓ | ❓ | ❓ |
| Others | ❌ | ❌ | ❌ |

---

## SLASH COMMANDS

User-invoked commands triggered by `/command` syntax.

| Platform | Command Location | Format | Invocation | Notes |
|----------|-----------------|--------|------------|-------|
| **Claude Code** | `~/.claude/commands/` or plugin `commands/` | YAML frontmatter + MD | `/command-name` | Full support with allowed-tools |
| **Codex CLI** | N/A | N/A | N/A | Uses AGENTS.md sections instead |
| **Gemini CLI** | Extension `commands/` | TOML | `/command-name` | Extension-based |
| **Cursor** | `.cursor/commands/` | MD | Slash commands | Direct file mapping |
| **Windsurf** | `.windsurf/workflows/` | MD | ❓ | Called workflows |
| **Roo Code** | `.roo/commands/` | MD | Slash commands | Direct file mapping |
| **Kiro** | N/A | N/A | Uses steering | No dedicated commands |
| **GitHub Copilot** | `.github/prompts/` | MD | @ references | Different invocation style |
| **Aider** | Built-in | N/A | `/add`, `/model`, etc. | Built-in commands only |
| **Continue** | N/A | N/A | ❓ | ❓ |
| **OpenCode** | N/A | N/A | ❓ | ❓ |
| **Agent Zero** | N/A | N/A | N/A | No slash commands |
| **Qoder** | N/A | N/A | ❓ | ❓ |
| **Trae** | ❓ | ❓ | ❓ | Needs research |

---

## HOOKS

Event-driven automation triggered by tool use, session events, or other lifecycle moments.

| Platform | Hook Location | Format | Events Supported | Notes |
|----------|--------------|--------|------------------|-------|
| **Claude Code** | `settings.json` or `hooks/hooks.json` | JSON | PreToolUse, PostToolUse, Stop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification, SubagentStart, SubagentStop, PermissionRequest, PostToolUseFailure | Full hook system |
| **Gemini CLI** | Extension `hooks/hooks.json` | JSON | Similar to Claude | Within extensions only |
| **Kiro** | `.kiro/hooks/` | MD/JSON | Prompt Submit, Agent Stop | Contextual hooks |
| **Roo Code** | Via custom modes | YAML | Mode-based triggers | Limited to mode changes |
| **Cursor** | N/A | N/A | ❌ | No hook system |
| **Windsurf** | N/A | N/A | ❌ | No hook system |
| **GitHub Copilot** | N/A | N/A | ❌ | No hook system |
| **Codex CLI** | `rules/*.rules` | Custom | Command patterns | Rule-based approval only |
| **Aider** | N/A | N/A | ❌ | No hook system |
| **Continue** | N/A | N/A | ❌ | No hook system |
| **OpenCode** | N/A | N/A | ❓ | Needs research |
| **Agent Zero** | N/A | N/A | ❌ | No hook system |
| **Qoder** | N/A | N/A | ❓ | Needs research |
| **Trae** | ❓ | ❓ | ❓ | Needs research |

---

## PLUGINS / EXTENSIONS

Packaged bundles of skills, commands, hooks, and MCP servers.

| Platform | Plugin Location | Manifest File | Can Include | Distribution |
|----------|----------------|---------------|-------------|--------------|
| **Claude Code** | `~/.claude/plugins/` | `.claude-plugin/plugin.json` | Commands, Agents, Skills, Hooks, MCP | Git repos, local dirs |
| **Gemini CLI** | `~/.gemini/extensions/` | `gemini-extension.json` | Skills, Commands, Hooks, MCP, Context | `gemini extensions install` |
| **Kiro** | `~/.kiro/powers/` | ❓ | MCP, Steering, Hooks | "Powers" system |
| **Cursor** | Via marketplace | N/A | ❓ | VS Code extension style |
| **Windsurf** | Via marketplace | N/A | ❓ | VS Code extension style |
| **Roo Code** | VS Code extension | N/A | Modes, Rules | VS Code marketplace |
| **Continue** | N/A | N/A | ❓ | Hub-based |
| **GitHub Copilot** | N/A | N/A | N/A | Built-in extensions only |
| **Codex CLI** | N/A | N/A | ❌ | No plugin system |
| **Aider** | N/A | N/A | ❌ | No plugin system |
| **OpenCode** | N/A | N/A | ❓ | Needs research |
| **Agent Zero** | `python/tools/` | N/A | Tools, Instruments | "Instruments" system |
| **Qoder** | Via settings | N/A | MCP | MCP-based only |
| **Trae** | ❓ | ❓ | ❓ | Needs research |

---

## MCP SERVERS

Model Context Protocol server integration for external tools and data sources.

| Platform | MCP Config Location | Format | Transport Types | Notes |
|----------|---------------------|--------|-----------------|-------|
| **Claude Code** | `~/.claude/.mcp.json` or plugin `.mcp.json` | JSON | stdio, SSE, HTTP | Full support |
| **Gemini CLI** | Extension manifest `mcpServers` | JSON | stdio, SSE, HTTP | Path uses `${extensionPath}` |
| **Cursor** | `.cursor/mcp.json` or settings | JSON | stdio, SSE, HTTP | Full support, Docker gateway available |
| **Windsurf** | `mcp_config.json` or settings | JSON | stdio, Streamable HTTP | MCP Marketplace |
| **Kiro** | `.kiro/settings/mcp.json` | JSON | stdio, Streamable HTTP | Remote MCP support |
| **Continue** | `.continue/mcpServers/` | JSON | stdio, SSE, Streamable HTTP | Directory-based |
| **Roo Code** | Via settings | JSON | stdio | MCP support |
| **GitHub Copilot** | Via settings or remote | JSON | Local or Remote | GitHub MCP Registry |
| **OpenCode** | ❓ | ❓ | ❓ | Needs research |
| **Agent Zero** | `conf/` | YAML | stdio, SSE, Streamable HTTP | Bidirectional (server + client) |
| **Qoder** | Settings → MCP | JSON | ❓ | MCP Marketplace |
| **Codex CLI** | N/A | N/A | ❌ | No MCP support |
| **Aider** | N/A | N/A | ❌ | No MCP support |
| **Trae** | Config file | YAML | stdio | `mcp_servers` section |

---

## AGENTS / MODES

Specialized personas or roles with different tool access and behaviors.

| Platform | Agent Location | Format | Features |
|----------|---------------|--------|----------|
| **Claude Code** | `~/.claude/agents/` | YAML frontmatter + MD | name, description, tools, model, color |
| **Codex CLI** | `~/.codex/AGENTS.md` | Plain MD | Aggregated single file |
| **Roo Code** | `custom_modes.yaml` or `.roomodes` | YAML/JSON | Modes with tool groups (read, edit, browser, command, mcp) |
| **Kiro** | `~/.kiro/steering/AGENTS.md` | MD | AGENTS.md standard |
| **Cursor** | N/A | N/A | Built-in modes only |
| **Windsurf** | N/A | N/A | Built-in Cascade modes |
| **OpenCode** | Built-in | N/A | build, plan agents + @general subagent |
| **GitHub Copilot** | N/A | N/A | Built-in Explore, Task agents |
| **Gemini CLI** | N/A | N/A | Convert to skills |
| **Agent Zero** | `agents/` | MD/Python | Subordinate agent profiles |
| **Aider** | Built-in | N/A | /architect, /ask modes |
| **Continue** | N/A | N/A | ❓ |
| **Qoder** | In-app | N/A | Customizable agents (TRAE 2.0) |
| **Trae** | In-app | N/A | Custom agents |

---

## CONTEXT FILES

Global instruction files that apply to all sessions.

| Platform | Context File | Location | Format |
|----------|-------------|----------|--------|
| **Claude Code** | `CLAUDE.md` | `~/.claude/` or project root | MD |
| **Gemini CLI** | `GEMINI.md` | `~/.gemini/` or project root | MD (hierarchical) |
| **Codex CLI** | `AGENTS.md` | `~/.codex/` or project root | MD |
| **OpenCode** | `AGENTS.md` | Project root | MD |
| **Cursor** | `.cursorrules` or `.cursor/rules/` | Project root | MD/MDC |
| **Windsurf** | `.windsurfrules` | Project root | MD |
| **Roo Code** | `.roo/rules-{mode}/` | Project root | MD |
| **Kiro** | `~/.kiro/steering/` + project | Global + project | MD |
| **GitHub Copilot** | `.github/copilot-instructions.md` | Repo root | MD |
| **Aider** | `CONVENTIONS.md` | Project root | MD |
| **Continue** | ❓ | ❓ | ❓ |
| **Agent Zero** | `prompts/default/agent.system.md` | prompts/ | MD |
| **Qoder** | Memory settings | In-app | Plain text |
| **Trae** | ❓ | ❓ | ❓ |

---

## TOOL RESTRICTIONS

How each platform controls which tools/capabilities are available.

| Platform | Restriction Type | Format | Notes |
|----------|-----------------|--------|-------|
| **Claude Code** | `allowed-tools` | Whitelist (YAML list) | Only listed tools permitted |
| **Gemini CLI** | `excludeTools` | Blacklist (JSON array) | Listed tools blocked |
| **Cursor** | N/A | N/A | No per-skill restrictions |
| **Windsurf** | N/A | N/A | No per-skill restrictions |
| **Roo Code** | `groups` | Group-based (read, edit, browser, command, mcp) | Mode-specific restrictions |
| **Kiro** | ❓ | ❓ | Needs research |
| **GitHub Copilot** | N/A | N/A | No restrictions |
| **Codex CLI** | `rules/*.rules` | Pattern-based | Command approval patterns |
| **Aider** | N/A | N/A | No restrictions |
| **Continue** | N/A | N/A | ❓ |
| **OpenCode** | N/A | N/A | ❓ |
| **Agent Zero** | N/A | N/A | No restrictions |
| **Qoder** | N/A | N/A | ❓ |
| **Trae** | N/A | N/A | ❓ |

---

## CONFIGURATION FILES SUMMARY

| Platform | Main Config | Settings | Skills/Rules |
|----------|-------------|----------|--------------|
| **Claude Code** | `~/.claude/settings.json` | JSON | `skills/`, `commands/`, `hooks/` |
| **Codex CLI** | `~/.codex/config.toml` | TOML | `skills/`, `rules/` |
| **Gemini CLI** | `~/.gemini/settings.json` | JSON | `skills/`, `extensions/` |
| **Cursor** | `.cursor/` + settings | JSON | `rules/`, `commands/` |
| **Windsurf** | Settings UI | JSON | `workflows/` |
| **Roo Code** | `custom_modes.yaml` | YAML | `commands/`, `rules/` |
| **Kiro** | `~/.kiro/settings/` | JSON | `steering/`, `hooks/` |
| **GitHub Copilot** | VS Code settings | JSON | `.github/prompts/` |
| **OpenCode** | `opencode.json` | JSON | `skills/` |
| **Continue** | `.continue/config.yaml` | YAML | `mcpServers/` |
| **Agent Zero** | `conf/` | YAML | `prompts/`, `agents/` |
| **Aider** | `.aider.conf.yml` | YAML | `CONVENTIONS.md` |
| **Qoder** | Settings UI | N/A | Memory settings |
| **Trae** | Config file | YAML | `skills/` |

---

## SYNC COMPATIBILITY MATRIX

Based on format similarity, here's what can be directly synced vs. needs conversion:

| From → To | Direct Copy | Needs Conversion | Not Compatible |
|-----------|:-----------:|:----------------:|:--------------:|
| Claude → Codex Skills | ✅ | | |
| Claude → Gemini Skills | ✅ | | |
| Claude → OpenCode Skills | ✅ | | |
| Claude → Trae Skills | ✅ | | |
| Claude → Cursor | | ⚠️ Remove frontmatter | |
| Claude → Windsurf | | ⚠️ Remove frontmatter | |
| Claude → Roo Code | | ⚠️ Remove frontmatter | |
| Claude → Kiro | | ⚠️ Remove frontmatter | |
| Claude → GitHub Copilot | | ⚠️ Rename to .prompt.md | |
| Claude → Aider | | ⚠️ Merge to CONVENTIONS.md | |
| Claude Hooks → Gemini | ✅ | | |
| Claude Hooks → Kiro | | ⚠️ Format conversion | |
| Claude MCP → Gemini | | ⚠️ Add ${extensionPath} | |
| Claude MCP → Cursor | ✅ | | |
| Claude MCP → Windsurf | ✅ | | |
| Claude MCP → Kiro | ✅ | | |

---

## SOURCES

- [Claude Code Docs](https://code.claude.com/docs)
- [Codex CLI GitHub](https://github.com/openai/codex)
- [Gemini CLI Docs](https://geminicli.com/docs)
- [Cursor Docs](https://cursor.com/docs)
- [Windsurf Docs](https://docs.windsurf.com)
- [Roo Code Docs](https://docs.roocode.com)
- [Kiro Docs](https://kiro.dev)
- [GitHub Copilot Docs](https://docs.github.com/copilot)
- [Continue.dev Docs](https://docs.continue.dev)
- [OpenCode Docs](https://opencode.ai/docs)
- [Agent Zero GitHub](https://github.com/agent0ai/agent-zero)
- [Aider Docs](https://aider.chat/docs)
- [Trae GitHub](https://github.com/bytedance/trae-agent)
- [Qoder Docs](https://docs.qoder.com)
- [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) - Multi-platform skill reference

---

## GAPS / NEEDS RESEARCH

The following areas need more research:

1. **CodeBuddy** - Could not find official documentation for this platform
2. **Trae** - Limited documentation on hooks, commands, and full plugin support
3. **Continue** - Skills subdirectory support unclear
4. **Qoder** - Detailed plugin/hook architecture undocumented
5. **OpenCode** - MCP configuration format needs verification

---

*Last updated: January 2026*
