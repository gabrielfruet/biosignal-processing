# Biosignal-tex Skill

Project-specific skill for updating the academic document after pipeline stages.

## How It Works

This skill is **generic** - it dynamically analyzes any stage's JSON metrics without hardcoded rules.

### Workflow

```
User: "Update document with Stage N results"
    │
    ▼
Agent reads: .pi/skills/biosignal-tex/SKILL.md
    │
    ▼
Agent creates dynamic analysis script (based on template)
    │
    ▼
Run: python analyze_metrics.py <stage> --explore
    │
    ▼
Understand JSON structure, extract key values
    │
    ▼
Generate .tex content with REAL values
    │
    ▼
Validate: cd tex && make
    │
    ▼
Update: docs/NEW_SESSION.md
```

## Usage

```bash
# List all stages
python3 .pi/skills/biosignal-tex/analyze_metrics.py --all

# Explore JSON structure
python3 .pi/skills/biosignal-tex/analyze_metrics.py 5 --explore

# Analyze values
python3 .pi/skills/biosignal-tex/analyze_metrics.py 5
```

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main instructions for the agent |
| `analyze_metrics.py` | Generic JSON explorer script |
| `README.md` | This file |

## Example Output

```
$ python analyze_metrics.py 5

Found 17 JSON file(s) in output/stage5_segmentation/metrics

============================================================
STAGE 5 ANALYSIS: Segmentation
============================================================

Numeric patterns found:

  Windows-related:
    metrics.eeg.n_windows_total: 28
    metrics.eeg.n_windows_usable: 23
    metrics.ecg.n_windows_total: 51
    ...

  Rates/percentages:
    stability.eeg.stability_rate: 100.00%
    stability.ecg.stability_rate: 18.75%
    ...
```

## Key Principle

> **Never fabricate values.** Always explore the actual JSON structure first, then extract real numbers for the document.
