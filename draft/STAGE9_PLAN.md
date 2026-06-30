# Stage 9: Feature Selection — Plan

## Context

Stage 8 produced PCA-reduced feature matrices (at 95% cumulative variance threshold) stored as
`{mod}_pca_reduced.csv` in `output/stage8_dimreduction/data/`. These are the clean numeric
representation used for downstream classification. Stage 9 ranks and selects the most informative
principal components (and underlying original features) using three complementary selection families.

**The response variable is `phase`** (baseline / stimulation / recovery) — the only available label
derived from the experimental protocol.

**Input data:**
| Modality | Observations | PC columns | phase balance |
|----------|-------------|------------|---------------|
| EEG      | 375         | 38 PCs     | 125/125/125 (balanced) |
| ECG      | 41          | 22 PCs     | ~14/14/13 |
| EMG      | 37          | 18 PCs     | ~13/12/12 |

---

## Files to Create / Edit

| File | Action |
|------|--------|
| `src/biosignal/stages/selection.py` | **Create** — full feature selection module |
| `src/biosignal/config.py` | **Edit** — add STAGE9 path constants |
| `src/biosignal/stages/__init__.py` | **Edit** — add `selection` import |
| `tex/2-textuais/3-metodologia.tex` | **Edit** — add Stage 9 methodology section |
| `tex/2-textuais/4-resultados.tex` | **Edit** — add Stage 9 results section |

---

## Implementation Plan

### 1. `src/biosignal/config.py` — STAGE9 constants

```python
STAGE9_DIR = OUTPUT_DIR / "stage9_selection"
STAGE9_METRICS_DIR = STAGE9_DIR / "metrics"
STAGE9_FIGURES_DIR = STAGE9_DIR / "figures"
STAGE9_DATA_DIR    = STAGE9_DIR / "data"
```

---

### 2. `src/biosignal/stages/selection.py`

#### Per-modality workflow

For each modality:
1. Load `output/stage8_dimreduction/data/{mod}_pca_reduced.csv`
2. Separate: `X` = PC columns, `y` = phase (encoded 0/1/2)
3. Apply 3 selection methods:

**SEL-001 — Filter methods (ANOVA F-test + Mutual Information):**
- `sklearn.feature_selection.f_classif(X, y)` → F-statistic + p-value per PC
- `sklearn.feature_selection.mutual_info_classif(X, y, random_state=42)` → MI score per PC
- Apply Bonferroni correction to ANOVA p-values (SEL-005)
- Compute Cohen's f² effect size per PC: `f² = F * (k-1) / (n - k)` where k=3 classes (SEL-006)

**SEL-002 — Wrapper: Recursive Feature Elimination (RFE):**
- `sklearn.feature_selection.RFECV` with `LinearSVC(max_iter=5000)` estimator
- 5-fold stratified cross-validation
- Record optimal number of features and ranking

**SEL-003 — Embedded: L1-regularised Linear SVC:**
- `sklearn.svm.LinearSVC(penalty='l1', dual=False, max_iter=5000)`
- Train on full X, read `coef_` magnitude per PC
- Features with non-zero coefficient in any class are "selected"

#### Feature ranking (SEL-004)

Combine three scores into a consensus rank:
- `anova_rank`: rank by F-statistic descending
- `mi_rank`: rank by MI score descending
- `coef_rank`: rank by max |coef| across classes descending
- `consensus_rank` = mean of the three rank positions (lower = better)
- Export `feature_ranking.json` sorted by consensus rank

#### Output per modality

**CSV** — `STAGE9_DATA_DIR/{mod}_selected.csv`:
- Same rows as input, only keeping PCs with `consensus_rank` ≤ `n_rfe_optimal`

**JSON** — `STAGE9_METRICS_DIR/{mod}_selection.json`:
```json
{
  "modality": "eeg",
  "n_pcs_input": 38,
  "n_selected_anova": N,
  "n_selected_rfe": N,
  "n_selected_l1": N,
  "n_selected_consensus": N,
  "feature_ranking": [{"feature": "PC1", "anova_f": ..., "anova_p": ..., "anova_p_bonf": ..., "mi": ..., "cohens_f2": ..., "coef_max": ..., "consensus_rank": ...}]
}
```

**Global** — `STAGE9_METRICS_DIR/selection_metrics.json`

#### Visualisations

1. **ANOVA F-bar** — F-statistic per PC, coloured red if Bonferroni-significant
   - `STAGE9_FIGURES_DIR/anova_fscores_{mod}.png`
2. **MI scores bar** — Mutual information per PC
   - `STAGE9_FIGURES_DIR/mi_scores_{mod}.png`
3. **RFE CV curve** — cross-val score vs number of features selected
   - `STAGE9_FIGURES_DIR/rfe_cv_{mod}.png`
4. **Consensus ranking heatmap** — PCs × methods, coloured by rank score (top 15 PCs)
   - `STAGE9_FIGURES_DIR/consensus_ranking_{mod}.png`

---

### 3. LaTeX — `3-metodologia.tex`

Add `\section{Seleção de Atributos}` before `\section{Estrutura do Pipeline}`:
- Subsection: Métodos de Filtro (ANOVA, MI, correções múltiplas, Cohen's f²)
- Subsection: Método Envoltório (RFECV)
- Subsection: Método Embutido (SVC-L1)
- Subsection: Ranking de Consenso

### 4. LaTeX — `4-resultados.tex`

Append `\section{Seleção de Atributos}` at end:
- Table: n_pcs_input, n_selected per method, consensus per modality
- ANOVA F-bar figures
- RFE CV curve figures
- Consensus ranking heatmap
- Narrative per modality

---

## Acceptance Criteria

- `output/stage9_selection/data/{eeg,ecg,emg}_selected.csv` exist
- `output/stage9_selection/metrics/selection_metrics.json` exists with `feature_ranking` per modality
- 4 figure types × 3 modalities = 12 figures
- `draft/STAGE9_PROGRESS.md` has real numbers from JSON
- LaTeX compiles without errors

---

## CLI

```bash
uv run python -m biosignal run 9 --verbose
```
