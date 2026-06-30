# Stage 10: Final Statistical Validation — Progress Report

## Execution Date
May 22, 2026

## Status: ✅ Complete

All 3 modalities validated. Final cross-modal dataset assembled.

---

## Implementation Summary

### Files Created/Modified

| File | Action |
|------|--------|
| `src/biosignal/config.py` | Added `STAGE10_DIR`, `STAGE10_METRICS_DIR`, `STAGE10_FIGURES_DIR`, `STAGE10_DATA_DIR` |
| `src/biosignal/stages/validation.py` | **Created** — full validation module |
| `src/biosignal/stages/__init__.py` | Added `validation` import |
| `draft/STAGE10_PLAN.md` | **Created** |

---

## Input Data (from Stage 9)

| Modality | Observations | Selected PCs | Phase balance |
|----------|-------------|--------------|---------------|
| EEG      | 375         | 36           | 125/125/125 |
| ECG      | 41          | 10           | 14/14/13 |
| EMG      | 37          | 16           | 14/12/11 |

---

## Validation Results

### VAL-001: Multicollinearity (VIF)

All VIF values are exactly 1.000 for all modalities — a mathematical guarantee since PCA
components are orthogonal by construction. No multicollinearity present.

| Modality | VIF mean | VIF max | n_high (≥5) | Status |
|----------|----------|---------|-------------|--------|
| EEG      | 1.000    | 1.000   | 0           | ✅ OK  |
| ECG      | 1.000    | 1.000   | 0           | ✅ OK  |
| EMG      | 1.000    | 1.000   | 0           | ✅ OK  |

### VAL-002: Phase Separability

| Modality | Top PC | ANOVA F | η²    | Pillai trace | Sep. OK |
|----------|--------|---------|-------|-------------|---------|
| EEG      | PC29   | 16.53   | 0.082 | 0.516       | ✅      |
| ECG      | PC19   | 3.71    | 0.163 | 0.776       | ✅      |
| EMG      | PC15   | 4.43    | 0.207 | 1.134       | ✅      |

**Bhattacharyya distances (top PC, phase pairs):**

| Modality | baseline vs recovery | baseline vs stimulation | recovery vs stimulation |
|----------|---------------------|------------------------|------------------------|
| EEG      | 0.164               | 0.041                  | 0.042                  |
| ECG      | 0.258               | 0.211                  | 0.010                  |
| EMG      | 0.376               | 0.115                  | 0.078                  |

### VAL-003: Class Balance

| Modality | baseline | stimulation | recovery | Imbalance ratio | Status |
|----------|----------|-------------|----------|-----------------|--------|
| EEG      | 125      | 125         | 125      | 1.00            | ✅ OK  |
| ECG      | 13       | 14          | 14       | 1.08            | ✅ OK  |
| EMG      | 12       | 11          | 14       | 1.27            | ✅ OK  |

All modalities below the 1.5 imbalance threshold. EEG is perfectly balanced.

### VAL-005: Dataset Final

| Property | Value |
|----------|-------|
| Path | `output/stage10_validation/data/dataset_final.csv` |
| Subjects (inner join) | 13 of 16 |
| Observations | 30 (13 subjects × ~3 phases, inner join) |
| Total features | 62 (36 EEG + 10 ECG + 16 EMG) |
| All modalities ready | ✅ |

---

## Output Files

### Data (1 CSV)
- `output/stage10_validation/data/dataset_final.csv` — cross-modal joined dataset

### Metrics (4 JSONs)
- `output/stage10_validation/metrics/{eeg,ecg,emg}_validation.json`
- `output/stage10_validation/metrics/final_validation.json`

### Figures (9 PNGs)
- `density_{eeg,ecg,emg}.png` — KDE per phase for top 3 PCs
- `vif_{eeg,ecg,emg}.png` — VIF bar chart per PC
- `class_balance_{eeg,ecg,emg}.png` — observation counts per phase

---

## Key Observations

1. **VIF = 1.0 exactly:** Confirms mathematical correctness of PCA — orthogonal components
   have zero linear dependence. Stage 10 VIF check is a sanity test that also validates
   the Stage 8 implementation.

2. **EEG most separable by ANOVA:** PC29 has the highest F-statistic (16.53) and is
   Bonferroni-significant. The Pillai trace of 0.516 indicates moderate multivariate
   separability.

3. **EMG highest η²:** PC15 shows η²=0.207 (medium effect size) — the highest single-component
   effect among all modalities, and the largest Bhattacharyya distance (0.376 between baseline
   and recovery), suggesting the muscle activity profile differs most clearly between those phases.

4. **ECG minimal phase separation:** The highest ECG Bhattacharyya distance (0.258, baseline
   vs recovery) is modest. The near-chance Stage 9 CV accuracy (36.7%) and low ANOVA F-scores
   confirm ECG provides limited discriminative power for the three-phase protocol.

5. **Dataset final inner join loses 3 subjects:** ECG (1 subject missing) and EMG (2 subjects
   missing) reduce the cross-modal joined dataset to 13 subjects × 30 observations. The EEG-only
   dataset (375 obs) remains available for single-modality classification.

6. **Pipeline complete:** All 10 stages implemented and validated. The dataset is ready for
   SVM, k-NN, Random Forest, and neural network classifiers.

---

## Integration Points

| Stage | Connection |
|-------|------------|
| Stage 9 (Selection) | Reads `output/stage9_selection/data/{mod}_selected.csv` |
| ML Classifiers | Reads `output/stage10_validation/data/dataset_final.csv` |

---

## Open Items

1. **Cross-modal fusion:** The inner-join dataset has only 30 observations for 62 features —
   very underdetermined. For multi-modal classification, consider late fusion (train per-modality
   classifiers, combine predictions) rather than feature concatenation.
2. **Leave-one-subject-out evaluation:** With n=13 cross-modal subjects, LOSO CV would provide
   more reliable generalisation estimates than random stratified k-fold.
3. **EEG-only path:** The 375-observation EEG dataset provides the most robust classification
   substrate; single-modality EEG experiments should use `eeg_selected.csv` directly.
