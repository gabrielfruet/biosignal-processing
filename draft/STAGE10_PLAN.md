# Stage 10: Final Statistical Validation — Plan

## Context

Stage 9 produced consensus-selected subsets of PCA components stored as `{mod}_selected.csv`
in `output/stage9_selection/data/`. Stage 10 validates the final dataset's readiness for
machine learning by checking: multicollinearity (VIF), phase separability, and class balance.
It also assembles the cross-modal `dataset_final.csv` deliverable required by PRD VAL-005.

**Input data:**
| Modality | Observations | Selected PCs | Phase balance |
|----------|-------------|--------------|---------------|
| EEG      | 375         | 36           | 125/125/125 (balanced) |
| ECG      | 41          | 10           | ~14/14/13 |
| EMG      | 37          | 16           | ~13/12/11 (approx.) |

---

## Files to Create / Edit

| File | Action |
|------|--------|
| `src/biosignal/stages/validation.py` | **Create** — full validation module |
| `src/biosignal/config.py` | **Edit** — add STAGE10 path constants |
| `src/biosignal/stages/__init__.py` | **Edit** — add `validation` import |
| `tex/2-textuais/3-metodologia.tex` | **Edit** — add Stage 10 methodology section |
| `tex/2-textuais/4-resultados.tex` | **Edit** — add Stage 10 results section |

---

## Implementation Plan

### 1. `src/biosignal/config.py` — STAGE10 constants

```python
STAGE10_DIR = OUTPUT_DIR / "stage10_validation"
STAGE10_METRICS_DIR = STAGE10_DIR / "metrics"
STAGE10_FIGURES_DIR = STAGE10_DIR / "figures"
STAGE10_DATA_DIR    = STAGE10_DIR / "data"
```

---

### 2. `src/biosignal/stages/validation.py`

#### Per-modality workflow

For each modality:
1. Load `output/stage9_selection/data/{mod}_selected.csv`
2. Extract PC columns as X, `phase` as y

**VAL-001 — Multicollinearity check (VIF):**
- For each PC column j: `VIF_j = 1 / (1 - R²_j)` where `R²_j` is the R² from regressing
  PC_j on all other PCs
- Use `statsmodels.stats.outliers_influence.variance_inflation_factor`
- Since PCA components are orthogonal by construction, VIF should be ≈ 1 for all — validate this
- Flag any VIF > 5 (moderate) or > 10 (severe)
- Save mean/max VIF to metrics

**VAL-002 — Phase separability:**
- Per-modality MANOVA: `statsmodels.multivariate.manova.MANOVA`
  `MANOVA.from_formula('PC1 + PC2 + ... ~ phase', data=df).mv_test()`
- Pillai's trace statistic and p-value
- Pairwise Bhattacharyya distance between phase distributions for top 2 PCs
- Effect size: overall η² (eta-squared) from one-way ANOVA on PC scores

**VAL-003 — Class balance:**
- Count observations per phase
- Compute imbalance ratio: max_class / min_class
- Flag if ratio > 1.5

**VAL-004 — Class density curves:**
- KDE (kernel density estimate) per phase for the top 3 PCs by ANOVA F-score
- 3-panel figure: one row per PC, coloured by phase
- Save: `STAGE10_FIGURES_DIR/density_{mod}.png`

**VAL-005 — Dataset readiness:**
- Assemble cross-modal `dataset_final.csv`: join EEG, ECG, EMG selected on
  `(subject_id, phase)`, averaging across channels for each modality
- Record: n_subjects, n_features_total, n_observations, balance_ok, vif_ok, separability_p

#### Additional visualisations

1. **VIF bar chart** per modality
   - `STAGE10_FIGURES_DIR/vif_{mod}.png`
2. **Pairwise scatter matrix** of top 4 PCs coloured by phase
   - `STAGE10_FIGURES_DIR/scatter_matrix_{mod}.png`
3. **Class balance bar** per modality
   - `STAGE10_FIGURES_DIR/class_balance_{mod}.png`

#### Output

**CSV** — `STAGE10_DATA_DIR/dataset_final.csv`:
```
subject_id, phase, eeg_PC1..eeg_PC36, ecg_PC1..ecg_PC10, emg_PC1..emg_PC16
```
(inner join on subject_id × phase — only rows present in all 3 modalities)

**JSON** — `STAGE10_METRICS_DIR/{mod}_validation.json`:
```json
{
  "modality": "eeg",
  "n_observations": 375,
  "n_features": 36,
  "class_balance": {"baseline": 125, "stimulation": 125, "recovery": 125},
  "imbalance_ratio": 1.0,
  "balance_ok": true,
  "vif_mean": ..., "vif_max": ..., "vif_ok": true,
  "manova_pillai": ..., "manova_p": ...,
  "separability_ok": true
}
```

**JSON** — `STAGE10_METRICS_DIR/final_validation.json` (global summary + dataset_final stats)

---

### 3. LaTeX — `3-metodologia.tex`

Add `\section{Validação Estatística Final}` before `\section{Estrutura do Pipeline}`:
- Subsection: Verificação de Multicolinearidade (VIF)
- Subsection: Análise de Separabilidade (MANOVA, Bhattacharyya)
- Subsection: Balanceamento de Classes
- Subsection: Montagem do Dataset Final

### 4. LaTeX — `4-resultados.tex`

Append `\section{Validação Estatística Final}` at end:
- Table: per-modality VIF mean/max, MANOVA p, balance ratio, readiness verdict
- Density curves figure
- Class balance figure
- Dataset final summary paragraph

---

## Acceptance Criteria

- `output/stage10_validation/data/dataset_final.csv` exists
- `output/stage10_validation/metrics/final_validation.json` exists
- All 3 figure types for all 3 modalities (9 figures minimum)
- LaTeX compiles without errors
- All numbers in `.tex` match JSON

---

## CLI

```bash
uv run python -m biosignal run 10 --verbose
```
