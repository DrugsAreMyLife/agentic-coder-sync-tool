---
name: example-skill
description: An example skill that demonstrates the Claude Code skill format. Skills are directories containing a SKILL.md file and optional scripts, references, and assets.
---

# Example Skill

This skill demonstrates the standard skill format used by Claude Code and Gemini CLI.

## Directory Structure

```
example-skill/
├── SKILL.md           # Required - skill definition and instructions
├── scripts/           # Optional - executable scripts
│   └── run.py
├── references/        # Optional - documentation and schemas
│   └── api-docs.md
└── assets/            # Optional - templates, images, binaries
    └── template.json
```

## Usage

Invoke this skill when you need to perform the example task.

```bash
# Run the associated script
python "${SKILL_DIR}/scripts/run.py" --option value
```

## Notes

- Skills are auto-discovered from `~/.claude/skills/` and `~/.gemini/skills/`
- The `${SKILL_DIR}` variable points to the skill's directory
- Scripts should be executable and handle their own dependencies
