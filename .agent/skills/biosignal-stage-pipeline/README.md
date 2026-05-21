# Biosignal Stage Pipeline Skill

Automates the full lifecycle of a pipeline stage — from plan to compiled LaTeX.

## When to Use

When the user says:
- "run stage N"
- "implement stage N"
- "do stage N"
- "now, run stage 9"

## 9-Step Sequence

```
1. Read context (PRD, previous stage outputs, config, CLI)
2. Write draft/STAGE{N}_PLAN.md         ← BEFORE any code
3. Add config constants + update __init__.py
4. Implement src/biosignal/stages/{module}.py
5. Run: uv run python -m biosignal run N --verbose
6. Analyze outputs with analyze_metrics.py
7. Write draft/STAGE{N}_PROGRESS.md     ← AFTER run, with real numbers
8. Update docs/NEW_SESSION.md + docs/CONTEXT.md
9. Write LaTeX sections + compile 3×
```

## Key Rules

- **PLAN before code.** Always write the plan file first.
- **PROGRESS after run.** Always use real JSON numbers — never fabricate.
- **Compile 3×.** Always run pdflatex three times after adding new sections.
- **Analyze before writing .tex.** Always run `analyze_metrics.py {N}` first.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Full instructions (read this) |
| `README.md` | This quick reference |

## Related Skills

- `biosignal-tex` — analyze JSON metrics and generate LaTeX content
