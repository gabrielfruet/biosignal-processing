# Stage 8: Dimensionality Reduction — Plan

## Context

Stage 7 produced per-(subject, channel, phase) aggregated feature matrices stored as `_aggregated.csv`
files in `output/stage7_engineering/data/`. These contain ~220+ columns (mean/std/min/max of every
engineered feature) and serve as the input to the ML pipeline.

**Problem:** High dimensionality (224 EEG feature columns) relative to the number of observations
(375 EEG rows across 16 subjects) risks overfitting in downstream classification. Stage 8 applies
PCA to compress the feature space while retaining maximum variance.

**Input data:**
| Modality | Subjects | Observations (rows) | Feature columns |
|----------|----------|---------------------|-----------------|
| EEG      | 16       | 375                 | 224             |
| ECG      | 15       | 41                  | 200             |
| EMG      | 14       | 37                  | 168             |

---

## Files to Create / Edit

| File | Action |
|------|--------|
| `src/biosignal/stages/dimreduction.py` | **Create** — full PCA implementation |
| `src/biosignal/config.py` | **Edit** — add STAGE8 path constants |
| `src/biosignal/stages/__init__.py` | **Edit** — add `dimreduction` import |
| `tex/2-textuais/3-metodologia.tex` | **Edit** — add Stage 8 methodology section |
| `tex/2-textuais/4-resultados.tex` | **Edit** — add Stage 8 results section |

---

## Implementation Plan

### 1. `src/biosignal/config.py` — STAGE8 constants

```python
STAGE8_DIR = OUTPUT_DIR / "stage8_dimreduction"
STAGE8_METRICS_DIR = STAGE8_DIR / "metrics"
STAGE8_FIGURES_DIR = STAGE8_DIR / "figures"
STAGE8_DATA_DIR = STAGE8_DIR / "data"
```

---

### 2. `src/biosignal/stages/dimreduction.py`

#### Pre-processing per modality

1. Load all `s*_{mod}_aggregated.csv` files and concatenate
2. Separate metadata cols: `subject_id`, `channel`, `phase`, `n_windows`
3. Drop feature columns with >50% NaN (e.g., `zcr_norm_*` for EEG)
4. Fill remaining NaN with column median (imputation)
5. `sklearn.preprocessing.StandardScaler` — z-score normalise

#### PCA

- `sklearn.decomposition.PCA(n_components=None)` — full decomposition
- Record `explained_variance_ratio_` for all components
- Determine thresholds:
  - `n_components_90` — components explaining ≥ 90% cumulative variance
  - `n_components_95` — components explaining ≥ 95% cumulative variance
- Transform data with `n_components_95` and save as reduced CSV

#### Output per modality

**CSV** — `STAGE8_DATA_DIR/{mod}_pca_reduced.csv`:
```
subject_id, channel, phase, PC1, PC2, ..., PC_k
```

**Loadings CSV** — `STAGE8_DATA_DIR/{mod}_pca_loadings.csv`:
```
feature, PC1, PC2, ..., PC_k
```

**Metrics JSON** — `STAGE8_METRICS_DIR/{mod}_pca_metrics.json`:
```json
{
  "modality": "eeg",
  "n_samples": 375,
  "n_features_input": 220,
  "n_features_dropped": 4,
  "n_components_90": N,
  "n_components_95": N,
  "explained_variance_ratio": [...],
  "cumulative_variance": [...]
}
```

**Global summary** — `STAGE8_METRICS_DIR/dimreduction_metrics.json`

#### Visualisations (per modality)

1. **Scree plot** — bar chart of explained variance per component (first 20)
   - Saved: `STAGE8_FIGURES_DIR/scree_plot_{mod}.png`

2. **Cumulative variance curve** — line plot with 90% and 95% threshold lines
   - Saved: `STAGE8_FIGURES_DIR/cumulative_variance_{mod}.png`

3. **2D PCA scatter** — PC1 vs PC2, coloured by `phase`
   - Saved: `STAGE8_FIGURES_DIR/pca_scatter_{mod}.png`

4. **Loadings heatmap** — top 5 components × top 15 features by absolute loading
   - Saved: `STAGE8_FIGURES_DIR/pca_loadings_{mod}.png`
   - Style: lower-triangle not applicable (rectangular); text annotations, no spines, dpi=150

---

### 3. LaTeX — `3-metodologia.tex`

Add `\section{Redução de Dimensionalidade}` before `\section{Estrutura do Pipeline}`:
- Motivation (curse of dimensionality, ratio n_obs/n_features)
- PCA theory subsection
- Pre-processing (NaN drop, imputation, standardisation) subsection
- Component selection criterion (cumulative variance ≥ 90%)

### 4. LaTeX — `4-resultados.tex`

Add `\section{Redução de Dimensionalidade}` at end, with real numbers from JSON:
- Table: n_features_input, n_components_90, n_components_95, variance_retained per modality
- Scree plots figure
- Cumulative variance figure
- 2D scatter figure
- Loadings heatmap figure
- Narrative per modality

---

## Acceptance Criteria

- `output/stage8_dimreduction/data/{eeg,ecg,emg}_pca_reduced.csv` exist
- `output/stage8_dimreduction/metrics/dimreduction_metrics.json` exists
- All 4 figure types generated for all 3 modalities (12 figures total)
- LaTeX compiles without errors or undefined references
- All numbers in `.tex` match JSON output

---

## CLI

```bash
uv run python -m biosignal run 8 --verbose
```
