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
uv run python -m biosignal run 8 --verbose

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
| 7. Feature Engineering | ✅ | May 20, 2026 | `run 7` | `stage7_engineering/`, EEG:63col, ECG:57col, EMG:43col |
| 8. Dimensionality Reduction | ✅ | May 21, 2026 | `run 8` | `stage8_dimreduction/`, PCA 12 figures |

---

## Current State (May 21, 2026)

### Stage 8 Completed — PCA Results

| Modality | Obs | Features | PC@90% | PC@95% | PC1 var | PC2 var |
|----------|-----|----------|--------|--------|---------|---------|
| EEG      | 375 | 220      | 26     | 38     | 18.7%   | 15.7%   |
| ECG      | 41  | 172      | 18     | 22     | 17.9%   | 11.3%   |
| EMG      | 37  | 140      | 15     | 18     | 18.9%   | 16.1%   |

**Key findings:**

- EEG compression: 220 → 38 components (83% reduction at 95% variance)
- ECG: 28/200 columns dropped (lf_power/hf_power/lf_hf_ratio all NaN from 5s window limitation)
- EEG PC1 driven by delta² spectral power features; PC2 by normalised power in max aggregation
- Phase separation visible in EEG PC1×PC2 scatter; ECG/EMG less separable

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/PRD.md` | Full project requirements |
| `docs/ARCHITECTURE.md` | Project structure, CLI commands |
| `docs/CONTEXT.md` | Current project status |
| `docs/NEW_SESSION.md` | This file — quick reference |
| `src/biosignal/stages/dimreduction.py` | Stage 8 implementation |
| `src/biosignal/stages/engineering.py` | Stage 7 implementation |
| `src/biosignal/stages/features.py` | Stage 6 implementation |
| `src/biosignal/config.py` | Configuration constants |
| `tex/documento.tex` | Academic document (~57 pages, updated through Stage 8) |
| `output/stage7_engineering/data/` | 90 aggregated/engineered CSVs (Stage 8 input) |
| `output/stage8_dimreduction/data/` | 6 PCA reduced/loadings CSVs (Stage 9 input) |
| `output/stage8_dimreduction/metrics/dimreduction_metrics.json` | Global PCA summary |
| `draft/STAGE8_PLAN.md` | Stage 8 plan |
| `draft/STAGE8_PROGRESS.md` | Stage 8 progress report |

---

## Dataset Info

- **16 subjects** (s000–s015)
- **Modalities:** EEG (8ch @ 512 Hz), ECG (1ch @ 250 Hz), EMG (1ch @ 250 Hz), fNIRS excluded
- **Task:** Emotion induction (baseline 30s → stimulation 30s → recovery)

---

## LaTeX Document

**Location:** `tex/documento.tex` — ~57 pages, fully compiled

**Sections added through Stage 8:**
- `3-metodologia.tex`: Stages 6, 7, 8 methodology sections
- `4-resultados.tex`: Stages 6, 7, 8 results sections (all with real metrics)

**Compile:**
```bash
cd tex
pdflatex documento.tex  # run 3 times to resolve all cross-references
bibtex documento        # if bibliography changed
pdflatex documento.tex
pdflatex documento.tex
```

---

## Next Steps (Stage 9: Feature Selection)

### Stage 9 Requirements

- Input: `output/stage8_dimreduction/data/{mod}_pca_reduced.csv`
- Filter methods: ANOVA F-test, Mutual Information
- Wrapper method: Recursive Feature Elimination (RFE) with cross-validation
- Embedded method: L1-regularised classifier (Lasso/SVM-L1)
- Output: ranked feature list + selected feature subset CSV
- Evaluation: cross-validated classification accuracy before/after selection

---

## Important Notes

1. **Python package:** Uses `uv` for dependency management (`uv add <pkg>` to add deps)
2. **scikit-learn** added in Stage 8 — available for Stages 9–10
3. **Data location:** `data/ieee-multimodal-extracted/{subject_id}/`
4. **Output location:** `output/stage{N}_{name}/`
5. **fNIRS excluded:** Do not process fNIRS in Stages 6–10
6. **ECG limitation:** lf_power/hf_power/lf_hf_ratio are all NaN (5s windows insufficient for HRV spectral analysis)
7. **When updating docs:** Check `git log` for accurate dates per branch
8. **When updating LaTeX:** Run skill analyzer first: `python3 .agent/skills/biosignal-tex/analyze_metrics.py <N>`
9. **Cross-references:** Always compile pdflatex 3× after adding new sections
