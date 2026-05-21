# New Session Guide

## Project: Biosignal Processing Pipeline (BioSignal-Process)

**Goal:** Transform raw biosignal data (EEG, ECG, EMG) from IEEE Multimodal Emotion Recognition dataset into validated, feature-rich dataset for machine learning.

---

## Quick Start Commands

```bash
# Navigate to project
cd /home/pauloricms/Documents/Materias_UFC/Biossinais/biosignal-processing

# Run any pipeline stage
uv run python -m biosignal run <1-10>

# Run with verbose output
uv run python -m biosignal run 6 --verbose

# Run for specific subject
uv run python -m biosignal run 6 --subject 5 --verbose

# List available stages
uv run python -m biosignal list-stages
```

---

## Completed Pipeline Stages

| Stage | Status | Completed | Command | Key Output |
|-------|--------|-----------|---------|------------|
| 1. Acquisition | ✅ | Mar 24, 2025 | `run 1` | `stage1_acquisition/` |
| 2. SQI | ✅ | Apr 1, 2026 | `run 2` | `stage2_sqi/` |
| 3. Statistics | ✅ | Apr 7, 2026 | `run 3` | `stage3_statistics/` |
| 4. Cleaning | ✅ | Apr 16, 2026 | `run 4` | `stage4_cleaning/` |
| 5. Segmentation | ✅ | May 6, 2026 | `run 5` | `stage5_segmentation/`, 64 NPZ files |
| 6. Feature Extraction | ✅ | May 20, 2026 | `run 6` | `stage6_features/`, 2,780 rows |

---

## Current State (May 20, 2026)

### Stage 6 Completed — Feature Extraction Results

**Feature Matrix (All 16 Subjects):**

| Modality | Features | Observations | Notes |
|----------|----------|--------------|-------|
| EEG | 18 | 2,417 | 9 temporal + 4 spectral + 5 band powers |
| ECG | 20 | 216 | 13 general + 7 HRV (time + freq) |
| EMG | 13 | 147 | 9 temporal + 4 spectral |
| fNIRS | — | — | Excluded (< 2.5% window retention) |
| **Total** | — | **2,780** | — |

**Key Findings:**
- **EEG dominant band:** beta (41.7 µV²/Hz) > alpha (19.0 µV²/Hz)
- **ECG HRV:** mean RR = 731 ms (~82 bpm), SDNN = 105 ms, RMSSD = 132 ms
- **EMG:** mean RMS = 5,971 µV, mean freq = 27.4 Hz
- **Subjects s002, s015:** EMG had 0 usable windows (Stage 5 rejection)
- **Subject s013:** ECG had 0 usable windows

**Segmentation Results (from Stage 5):**

| Modality | Total Windows | Usable | Retention |
|----------|--------------|--------|-----------|
| EEG (8ch) | 329 | 309 | 93.9% |
| ECG | 334 | 216 | 64.7% |
| EMG | 334 | 147 | 44.0% |
| fNIRS | 314 | 8 | 2.5% |

---

## Next Steps (Stage 7: Feature Engineering)

### Stage 7 Requirements
- **ENG-001:** Band power ratios (alpha/beta, theta/alpha, etc.)
- **ENG-002:** Normalize features by baseline window
- **ENG-003:** Delta features (Δ, Δ²) — first and second derivatives across windows
- **ENG-004:** Temporal aggregations (mean/std/min/max per subject per modality)
- **ENG-005:** Correlation with response variable
- **ENG-006:** Feature redundancy analysis

### Stages 8-10
- Stage 8: Dimensionality Reduction (PCA, Scree plot)
- Stage 9: Feature Selection (ANOVA, Mutual Information, wrapper methods)
- Stage 10: Final Statistical Validation

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/PRD.md` | Full project requirements |
| `docs/ARCHITECTURE.md` | Project structure, CLI commands |
| `docs/CONTEXT.md` | Current project status |
| `docs/NEW_SESSION.md` | This file — quick reference |
| `src/biosignal/stages/features.py` | Stage 6 implementation |
| `src/biosignal/config.py` | Configuration constants |
| `tex/documento.tex` | Academic document (50 pages, updated with Stages 5–6) |
| `output/stage5_segmentation/data/segments/` | 64 NPZ segment files (Stage 6 input) |
| `output/stage6_features/data/` | 48 feature CSVs (Stage 7 input) |
| `output/stage6_features/metrics/features_metrics.json` | Global feature summary |
| `draft/STAGE6_PLAN.md` | Stage 6 plan |
| `draft/STAGE6_PROGRESS.md` | Stage 6 progress report |

---

## Dataset Info

- **16 subjects** (s000–s015)
- **Modalities:** EEG (8ch @ 512 Hz), ECG (1ch @ 250 Hz), EMG (1ch @ 250 Hz), fNIRS excluded
- **Task:** Emotion induction (baseline 30s → stimulation 30s → recovery)

---

## LaTeX Document

**Location:** `tex/documento.tex` — 50 pages, fully compiled

**Stage 6 Sections Added:**
- `3-metodologia.tex`: `\section{Extração de Atributos}` (3 subsections)
- `4-resultados.tex`: `\section{Extração de Atributos}` (5 subsections, real metrics)

**Compile:**
```bash
cd tex
pdflatex documento.tex  # run 2-3 times to resolve all cross-references
```

---

## Important Notes

1. **Python package:** Uses `uv` for dependency management
2. **Data location:** `data/ieee-multimodal-extracted/{subject_id}/`
3. **Output location:** `output/stage{N}_{name}/`
4. **fNIRS excluded:** Do not process fNIRS in Stages 6–10
5. **When updating docs:** Check `git log` for accurate dates per branch
6. **When updating LaTeX:** Always read JSON metrics first, then write `.tex` with real values
7. **Cross-references:** Always compile pdflatex 3× after adding new sections
