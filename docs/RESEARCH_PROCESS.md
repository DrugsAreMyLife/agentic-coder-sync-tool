# Platform Research & Enhancement Process

This document provides a reproducible process for researching AI coding platforms and keeping the sync tool up to date.

## Quick Research Checklist

Run this process quarterly or when adding new platforms:

```bash
# 1. Check for new platforms in the ecosystem
# Search GitHub for trending AI coding assistants
# Search terms: "AI coding assistant CLI", "agentic coder", "AI pair programmer"

# 2. For each platform, gather:
#    - Official documentation URL
#    - Configuration file locations
#    - Skill/prompt format specifications
#    - Hook/event system documentation
#    - MCP/tool integration specs
```

---

## Platform Research Template

When researching a new platform, collect the following information:

### Basic Information
| Field | Value |
|-------|-------|
| Platform Name | |
| Official Website | |
| Documentation URL | |
| GitHub Repository | |
| Latest Version | |
| Date Researched | |

### Configuration Locations

```
Global Config Path:
Project Config Path:
Skills/Prompts Path:
Hooks Path:
MCP Config Path:
Extensions/Plugins Path:
```

### Feature Support

| Feature | Supported | Location | Format |
|---------|-----------|----------|--------|
| Skills/Prompts | Yes/No | | |
| Slash Commands | Yes/No | | |
| Hooks/Events | Yes/No | | |
| Plugins/Extensions | Yes/No | | |
| MCP Servers | Yes/No | | |
| Custom Agents/Modes | Yes/No | | |
| Context Files | Yes/No | | |
| Tool Restrictions | Yes/No | | |

### Format Specifications

Document the exact format for each supported feature:

```markdown
# Skill Format Example
[paste example here]
```

```json
// Hook Format Example
[paste example here]
```

```json
// MCP Config Example
[paste example here]
```

---

## Research Sources by Platform

### Claude Code
- **Primary Docs**: https://docs.anthropic.com/en/docs/claude-code
- **Plugins Guide**: https://docs.anthropic.com/en/docs/claude-code/plugins
- **Hooks Reference**: https://docs.anthropic.com/en/docs/claude-code/hooks
- **MCP Integration**: https://docs.anthropic.com/en/docs/claude-code/mcp
- **GitHub Issues**: Check for new features/changes

### Codex CLI (OpenAI)
- **GitHub Repo**: https://github.com/openai/codex
- **README**: Primary documentation source
- **Config Schema**: Check `~/.codex/` structure
- **Skills**: `~/.codex/skills/` (SKILL.md format)

### Gemini CLI
- **Primary Docs**: https://googlegemini.github.io/gemini-cli/docs/
- **Extensions**: https://googlegemini.github.io/gemini-cli/docs/extensions/
- **Hooks**: https://googlegemini.github.io/gemini-cli/docs/extensions/hooks/
- **MCP Integration**: https://googlegemini.github.io/gemini-cli/docs/mcp/
- **GitHub**: https://github.com/google-gemini/gemini-cli

### Antigravity
- **Same as Gemini CLI** (shared format)
- **Path difference**: `~/.gemini/antigravity/` instead of `~/.gemini/`

### Cursor
- **Docs**: https://docs.cursor.com/
- **Rules**: https://docs.cursor.com/context/rules
- **MCP**: https://docs.cursor.com/context/model-context-protocol
- **Commands**: Built-in, limited customization

### Windsurf
- **Docs**: https://docs.windsurf.com/
- **Workflows**: https://docs.windsurf.com/windsurf/memories#workflows
- **MCP**: https://docs.windsurf.com/windsurf/mcp

### Roo Code
- **Docs**: https://docs.roocode.com/
- **Features**: https://docs.roocode.com/features/
- **Custom Modes**: https://docs.roocode.com/features/custom-modes
- **MCP**: https://docs.roocode.com/features/mcp/
- **Rules**: https://docs.roocode.com/features/rules/

### Kiro (AWS)
- **Docs**: https://kiro.dev/docs/
- **Steering**: https://kiro.dev/docs/steering/
- **Hooks**: https://kiro.dev/docs/hooks/
- **Powers (Extensions)**: https://kiro.dev/docs/powers/
- **MCP**: https://kiro.dev/docs/mcp/

### GitHub Copilot
- **Docs**: https://docs.github.com/en/copilot
- **Custom Instructions**: https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot
- **Prompts**: `.github/copilot-instructions.md`, `.github/prompts/*.prompt.md`

### Continue
- **Docs**: https://docs.continue.dev/
- **Skills**: Same SKILL.md format as Claude
- **MCP**: https://docs.continue.dev/customize/mcp
- **Config**: `~/.continue/`

### OpenCode
- **GitHub**: https://github.com/opencode-ai/opencode
- **Skills**: SKILL.md format (Claude-compatible)
- **Config**: `~/.opencode/`

### Trae
- **GitHub**: https://github.com/anthropic/trae (if applicable)
- **Skills**: SKILL.md format (Claude-compatible)
- **Config**: `~/.trae/`

### Aider
- **Docs**: https://aider.chat/docs/
- **Conventions**: https://aider.chat/docs/usage/conventions.html
- **Config**: `.aider.conf.yml`, `CONVENTIONS.md`

### Agent Zero
- **GitHub**: https://github.com/frdel/agent-zero
- **Prompts**: `prompts/` directory
- **Instruments**: `python/tools/` directory

---

## Verification Commands

Run these to verify current implementations:

```bash
# Check all platform paths exist
python3 -c "
from pathlib import Path
import os

paths = {
    'Claude': Path.home() / '.claude' / 'skills',
    'Codex': Path.home() / '.codex' / 'skills',
    'Gemini': Path.home() / '.gemini' / 'skills',
    'Antigravity': Path.home() / '.gemini' / 'antigravity' / 'skills',
    'Cursor': Path.home() / '.cursor',
    'Windsurf': Path.home() / '.windsurf',
    'Continue': Path.home() / '.continue',
    'OpenCode': Path.home() / '.opencode',
}

for name, path in paths.items():
    status = '✓' if path.exists() else '✗'
    print(f'{status} {name}: {path}')
"

# Verify sync_agents.py syntax
python3 -m py_compile src/sync_agents.py && echo "✓ Syntax OK"

# Run dry-run sync tests
python3 src/sync_agents.py --dry-run --source claude --target gemini
```

---

## Adding a New Platform

### Step 1: Research
1. Find official documentation
2. Install the platform locally if possible
3. Locate all configuration files
4. Document formats using the template above

### Step 2: Update Platform Registry

Add to `PLATFORMS` dict in `sync_agents.py`:

```python
"newplatform": {
    "name": "New Platform",
    "skill_format": "SKILL.md",  # or "*.md", "*.prompt.md", etc.
    "frontmatter": True,  # Does it use YAML frontmatter?
    "paths": {
        "global_config": Path.home() / ".newplatform",
        "skills": Path.home() / ".newplatform" / "skills",
        "hooks": Path.home() / ".newplatform" / "hooks.json",
        "mcp": Path.home() / ".newplatform" / "mcp.json",
    },
    "features": {
        "skills": True,
        "commands": False,
        "hooks": True,
        "plugins": False,
        "mcp": True,
        "agents": False,
        "context_files": True,
        "tool_restrictions": True,
    }
}
```

### Step 3: Implement Sync Methods

Create sync functions following this pattern:

```python
def sync_to_newplatform(source_skills: list[Path], target_dir: Path) -> dict:
    """Sync skills to New Platform format."""
    results = {"synced": [], "skipped": [], "errors": []}

    for skill_path in source_skills:
        try:
            # Read source skill
            content = skill_path.read_text()

            # Transform format if needed
            transformed = transform_skill_for_newplatform(content)

            # Write to target
            target_path = target_dir / skill_path.name
            target_path.write_text(transformed)

            results["synced"].append(str(target_path))
        except Exception as e:
            results["errors"].append(f"{skill_path}: {e}")

    return results


def sync_from_newplatform(source_dir: Path, target_skills: Path) -> dict:
    """Sync skills from New Platform to Claude format."""
    # Reverse transformation logic
    pass
```

### Step 4: Update Documentation

1. Add platform to `docs/platform-feature-matrix.md`
2. Add format examples to `docs/format-comparison.md`
3. Update `README.md` with new platform

### Step 5: Test

```bash
# Test syntax
python3 -m py_compile src/sync_agents.py

# Test dry run
python3 src/sync_agents.py --dry-run --source claude --target newplatform

# Test actual sync (with backup)
python3 src/sync_agents.py --backup --source claude --target newplatform
```

---

## Quarterly Maintenance Checklist

- [ ] Check each platform's official docs for breaking changes
- [ ] Search GitHub for new AI coding platforms
- [ ] Verify all documented paths still exist
- [ ] Run full test suite
- [ ] Update version numbers in docs
- [ ] Check for deprecated features
- [ ] Review GitHub issues/PRs for user-reported issues

---

## Known Platform Relationships

Some platforms share formats or codebases:

| Platform Group | Shared Format | Notes |
|----------------|---------------|-------|
| Claude, Codex, Gemini, Continue, OpenCode, Trae | SKILL.md with YAML frontmatter | Direct copy possible |
| Gemini, Antigravity | Identical | Same codebase, different paths |
| Cursor, Windsurf | Similar .md rules | Minor format differences |
| Roo Code | Unique .roorules | Custom format |

---

## Web Search Queries for Updates

Use these searches to find documentation updates:

```
site:docs.anthropic.com claude code 2024
site:github.com/openai/codex releases
site:googlegemini.github.io/gemini-cli changelog
site:docs.cursor.com changelog
site:docs.windsurf.com updates
site:docs.roocode.com releases
site:kiro.dev/docs changelog
site:docs.github.com copilot updates
site:docs.continue.dev changelog
```

---

## Troubleshooting Research Issues

### Platform Documentation Not Found
1. Check if platform was renamed
2. Search GitHub for the project
3. Check if it's part of a larger product (e.g., Kiro → AWS)
4. Look for community documentation

### Format Changed
1. Compare with previous saved examples
2. Check version/changelog for breaking changes
3. Test with minimal example first
4. Update transform functions incrementally

### Platform Deprecated
1. Add deprecation notice to docs
2. Keep sync code but add warning
3. Document migration path if available

---

## Research Log

Keep a log of research sessions:

| Date | Researcher | Platforms Checked | Changes Made | Notes |
|------|------------|-------------------|--------------|-------|
| 2025-01-23 | Claude | All 14 platforms | Initial full implementation | Based on official docs |
| | | | | |

---

## Contributing

When contributing platform research:

1. Use the template above
2. Include links to all sources
3. Provide code examples where possible
4. Test locally before submitting
5. Update the research log
