---
name: biosignal-stage-pipeline
description: "Full pipeline stage implementation workflow for the biosignal processing project. Use when the user asks to run, implement, or execute a pipeline stage (e.g. 'run stage 9', 'implement stage 9'). Handles the complete lifecycle: plan → implement → run → analyze → progress report → docs update → LaTeX write → compile."
---

# Biosignal Stage Pipeline Skill

## Purpose

Automates the full lifecycle of implementing a new pipeline stage. Every stage follows the **same 9-step sequence** — never skip steps, never change order.

---

## 9-Step Sequence

### STEP 1 — Read context

Before writing anything, read:
- `docs/PRD.md` — stage requirements (REQ-IDs, deliverables)
- `docs/NEW_SESSION.md` — current state, previous stage outputs
- The previous stage's PROGRESS file in `draft/` to understand input data shape
- `src/biosignal/config.py` — existing path constants
- `src/biosignal/cli.py` — module name the CLI expects (e.g. `dimreduction`, `selection`)
- `src/biosignal/stages/__init__.py` — current imports

Also inspect the previous stage's output directory:
```bash
ls output/stage{N-1}_*/data/ | head -10
python3 -c "import pandas as pd; df = pd.read_csv('output/stage{N-1}_*/data/FIRST_FILE.csv'); print(df.shape); print(list(df.columns)[:20])"
```

---

### STEP 2 — Write `draft/STAGE{N}_PLAN.md`

**Do this BEFORE writing any code.**

Use this exact structure (see `draft/STAGE7_PLAN.md` or `draft/STAGE8_PLAN.md` as canonical examples):

```markdown
# Stage N: {Name} — Plan

## Context
[What previous stage produced. Input data shape (rows × cols) per modality. Why this stage is needed.]

**Input data:**
| Modality | Subjects | Observations | Feature columns |
...

---

## Files to Create / Edit
| File | Action |
...

---

## Implementation Plan

### 1. `src/biosignal/config.py` — STAGE{N} constants
[code block with the 4 path constants]

### 2. `src/biosignal/stages/{module}.py`
[Function signatures, logic description, output CSV/JSON structure]

### 3. LaTeX — `3-metodologia.tex`
[Section name, subsections to add, where to insert]

### 4. LaTeX — `4-resultados.tex`
[Section name, tables/figures to include, where to insert]

---

## Acceptance Criteria
[Checkable list of output files and properties]

---

## CLI
[uv run python -m biosignal run N --verbose]
```

---

### STEP 3 — Add config constants + update `__init__.py`

In `src/biosignal/config.py`, append after the previous stage's block:
```python
# Stage N: {Name}
STAGE{N}_DIR = OUTPUT_DIR / "stage{N}_{dirname}"
STAGE{N}_METRICS_DIR = STAGE{N}_DIR / "metrics"
STAGE{N}_FIGURES_DIR = STAGE{N}_DIR / "figures"
STAGE{N}_DATA_DIR    = STAGE{N}_DIR / "data"
```

In `src/biosignal/stages/__init__.py`, add the new module to the import line and `__all__`.

---

### STEP 4 — Implement `src/biosignal/stages/{module}.py`

**Mandatory conventions:**
- Module docstring: one line describing the stage
- `matplotlib.use("Agg")` before any other matplotlib import
- `warnings.filterwarnings("ignore", category=RuntimeWarning)`
- All plots: `no spines`, `dpi=150`, `bbox_inches="tight"`, text annotations where applicable
- Correlation/heatmap plots: **lower-triangle only** style (same as Stage 3)
- `run(subject_id=None, verbose=False)` is the entry point
- Create all output dirs with `.mkdir(parents=True, exist_ok=True)` at start of `run()`
- Save a **global summary JSON** at the end: `{stage}{N}_metrics_dir/{stagename}_metrics.json`
- Handle missing input files gracefully (skip with a verbose print, don't crash)

---

### STEP 5 — Run the stage

```bash
uv run python -m biosignal run {N} --verbose
```

If it fails:
- Read the full traceback
- Fix the root cause
- Re-run until it exits with "Stage completed successfully!"
- Verify outputs exist: `ls output/stage{N}_*/data/ output/stage{N}_*/metrics/ output/stage{N}_*/figures/`

---

### STEP 6 — Analyze outputs with the skill analyzer

```bash
python3 .agent/skills/biosignal-tex/analyze_metrics.py {N} --explore
python3 .agent/skills/biosignal-tex/analyze_metrics.py {N}
```

Then run a targeted Python snippet to extract the exact numbers needed for the PROGRESS file and LaTeX:
```bash
python3 -c "
import json
with open('output/stage{N}_{dirname}/metrics/{stagename}_metrics.json') as f:
    d = json.load(f)
# Print all key metrics
"
```

**NEVER fabricate numbers.** Every number in PROGRESS and in `.tex` must come from the actual JSON.

---

### STEP 7 — Write `draft/STAGE{N}_PROGRESS.md`

Use `draft/STAGE7_PROGRESS.md` or `draft/STAGE8_PROGRESS.md` as canonical examples.

Required sections:
```markdown
# Stage N: {Name} — Progress Report

## Execution Date
{today's date}

## Status: ✅ Complete

---

## Implementation Summary
### Files Created/Modified
[Table: file → action]

---

## [Input Data section if applicable]

---

## Key Results
[Tables with real numbers from JSON]
[Top loadings / top features / key statistics]

---

## Output Files
[Data CSVs, Metric JSONs, Figure PNGs — counts and paths]

---

## Key Observations
[Numbered list of non-obvious findings]

---

## Integration Points
[Table: Stage N-1 → reads what; Stage N+1 → outputs what]

---

## Open Items
[Numbered list of limitations, deferred work, caveats]
```

---

### STEP 8 — Update `docs/NEW_SESSION.md` and `docs/CONTEXT.md`

**NEW_SESSION.md:**
- Add Stage N row to the "Completed Pipeline Stages" table with today's date
- Replace "Current State" section with Stage N results (key metrics table)
- Update "Key Files" table
- Update "Next Steps" to Stage N+1

**CONTEXT.md:**
- Update the Pipeline Stages table: change Stage N from `📋 Todo` → `✅ Complete` with key deliverables
- Add `### Stage N: {Name} ✅` subsection under "Current Progress" with date, output summary, key findings
- Update "Next Steps" to Stage N+1

---

### STEP 9 — Write LaTeX sections + compile

#### Methodology (`3-metodologia.tex`)

Insert a new `\section{{Stage Name}}` **before** `\section{Estrutura do Pipeline de Processamento}`.

Structure:
- Opening paragraph (what this stage does, why)
- 3–5 `\subsection` entries covering the main algorithmic steps
- Use `\label{sec:metodo_{keyword}}`
- Reference PRD requirements where appropriate
- For formulas: use `equation` environment with `\label{eq:...}`

#### Results (`4-resultados.tex`)

Append a new `\section{{Stage Name}}` at the **end of the file**.

Structure:
- Opening paragraph linking to methodology section via `\ref{sec:metodo_{keyword}}`
- At least one `\begin{table}...\end{table}` with real numbers
- `\begin{figure}...\end{figure}` blocks for each generated plot
  - Path: `../output/stage{N}_{dirname}/figures/{filename}.png`
  - Always include `\label{fig:...}` and `\caption{...}`
- Per-modality narrative paragraphs with exact numbers from JSON
- Use `$X{,}Y$` for Brazilian decimal notation (e.g. `$18{,}7\%$`)

#### Compile (always 3 passes):
```bash
cd tex
pdflatex -interaction=nonstopmode documento.tex
pdflatex -interaction=nonstopmode documento.tex
pdflatex -interaction=nonstopmode documento.tex
```

Check log for errors:
```bash
grep -i "undefined\|LaTeX Error\|Emergency stop" documento.log | head -10
```

If a new `\cite{}` was added, run bibtex between passes:
```bash
pdflatex documento.tex && bibtex documento && pdflatex documento.tex && pdflatex documento.tex
```

---

## Checklist (verify before declaring done)

- [ ] `draft/STAGE{N}_PLAN.md` exists
- [ ] `src/biosignal/config.py` has STAGE{N} constants
- [ ] `src/biosignal/stages/__init__.py` imports the new module
- [ ] `src/biosignal/stages/{module}.py` exists and runs without error
- [ ] All expected output files exist (data CSVs, metric JSONs, figure PNGs)
- [ ] `draft/STAGE{N}_PROGRESS.md` exists with real numbers (no fabricated values)
- [ ] `docs/NEW_SESSION.md` updated
- [ ] `docs/CONTEXT.md` updated
- [ ] `3-metodologia.tex` has new `\section`
- [ ] `4-resultados.tex` has new `\section` with real numbers matching JSON
- [ ] LaTeX compiles to PDF with no errors or undefined references

---

## Common Pitfalls

| Problem | Fix |
|---------|-----|
| `np.trapz` removed in NumPy 2.x | Use `np.trapezoid` |
| `No module named 'sklearn'` | `uv add scikit-learn` |
| Bare `Δ` in LaTeX subsection titles | Use `\texorpdfstring{$\Delta$}{Delta}` |
| Figure refs show `??` in PDF | Run pdflatex 3 times |
| `\cite{key}` undefined | Add entry to `tex/3-pos-textuais/referencias.bib`, then run bibtex |
| Legend warning "no artists" | Guard with `handles, labels = ax.get_legend_handles_labels(); if handles: ax.legend(...)` |
| `__init__.py` edit fails | Read the file first before editing |
| NaN columns crash PCA/scaler | Drop columns with >50% NaN before fitting |
| ECG lf/hf columns all NaN | Expected — 5s windows cannot resolve LF/HF bands; drop them and note in text |

---

## Stage Name Reference

| Stage | CLI name | Module | Output dirname |
|-------|----------|--------|----------------|
| 6 | features | features | stage6_features |
| 7 | engineering | engineering | stage7_engineering |
| 8 | dimreduction | dimreduction | stage8_dimreduction |
| 9 | selection | selection | stage9_selection |
| 10 | validation | validation | stage10_validation |
