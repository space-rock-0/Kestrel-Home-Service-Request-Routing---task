# skills/

One folder per skill, each with a `SKILL.md`:

```
skills/my-skill/SKILL.md
---
name: my-skill
description: One line on when to use it.
tools: tool_a, tool_b
---
Instructions for the agent, in markdown.
```

Skills load at startup and appear at `GET /api/extensions`. Read the text at `GET /api/extensions/skills/<name>` (use underscores for hyphens). `triage-review` is included as a working example.
