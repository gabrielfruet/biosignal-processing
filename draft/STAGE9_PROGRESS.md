# Stage 9: Feature Selection — Progress Report

## Execution Date
May 22, 2026

## Status: ✅ Complete

All 3 modalities processed through Filter, Wrapper (RFECV), and Embedded (L1-SVC) selection.

---

## Implementation Summary

### Files Created/Modified

| File | Action |
|------|--------|
| `src/biosignal/config.py` | Added `STAGE9_DIR`, `STAGE9_METRICS_DIR`, `STAGE9_FIGURES_DIR`, `STAGE9_DATA_DIR` |
| `src/biosignal/stages/selection.py` | **Created** — full feature selection module |
| `src/biosignal/stages/__init__.py` | Added `selection` import |
| `draft/STAGE9_PLAN.md` | **Created** |

---

## Input Data (from Stage 8)

| Modality | Observations | PCs input | Phase balance |
|----------|-------------|-----------|---------------|
| EEG      | 375         | 38        | 125/125/125 (balanced) |
| ECG      | 41          | 22        | ~14/14/13 |
| EMG      | 37          | 18        | ~13/12/12 |

---

## Selection Results

| Modality | PCs input | Sig (Bonferroni) | RFE optimal | L1 non-zero | Consensus | RFE CV acc |
|----------|-----------|-----------------|-------------|-------------|-----------|------------|
| EEG      | 38        | 2               | 36          | 38          | 36        | 65.6%      |
| ECG      | 22        | 0               | 10          | 19          | 10        | 36.7%      |
| EMG      | 18        | 0               | 16          | 15          | 16        | 53.9%      |

---

## Top Features by Consensus Rank

### EEG (top 5)

| Feature | ANOVA F | Bonf. sig | MI    | Cohen's f² | Consensus rank |
|---------|---------|-----------|-------|------------|----------------|
| PC29    | 16.53   | ✅        | 0.117 | 0.089      | 1.7            |
| PC13    | 5.25    | ❌        | 0.198 | 0.028      | 4.0            |
| PC6     | 9.05    | ✅        | 0.078 | 0.049      | 6.0            |
| PC2     | 3.23    | ❌        | 0.191 | 0.017      | 6.0            |
| PC8     | 5.79    | ❌        | 0.071 | 0.031      | 6.3            |

### ECG (top 5)

| Feature | ANOVA F | MI    | Cohen's f² | Consensus rank |
|---------|---------|-------|------------|----------------|
| PC22    | 2.19    | 0.024 | 0.115      | 3.3            |
| PC12    | 1.81    | 0.079 | 0.095      | 3.7            |
| PC21    | 1.45    | 0.048 | 0.076      | 4.0            |
| PC19    | 3.71    | 0.000 | 0.195      | 6.0            |
| PC20    | 1.43    | 0.000 | 0.075      | 8.7            |

### EMG (top 5)

| Feature | ANOVA F | MI    | Cohen's f² | Consensus rank |
|---------|---------|-------|------------|----------------|
| PC15    | 4.43    | 0.059 | 0.260      | 1.3            |
| PC11    | 2.60    | 0.036 | 0.153      | 3.0            |
| PC2     | 3.45    | 0.024 | 0.203      | 5.0            |
| PC8     | 2.45    | 0.007 | 0.144      | 5.0            |
| PC17    | 1.28    | 0.049 | 0.075      | 5.0            |

---

## Output Files

### Data (3 CSVs)
- `output/stage9_selection/data/{eeg,ecg,emg}_selected.csv` — consensus-selected PCs

### Metrics (4 JSONs)
- `output/stage9_selection/metrics/{eeg,ecg,emg}_selection.json`
- `output/stage9_selection/metrics/selection_metrics.json`

### Figures (12 PNGs)
- `anova_fscores_{eeg,ecg,emg}.png` — ANOVA F-bar with Bonferroni significance colouring
- `mi_scores_{eeg,ecg,emg}.png` — top 20 components by mutual information
- `rfe_cv_{eeg,ecg,emg}.png` — RFECV accuracy curve with optimal marker
- `consensus_ranking_{eeg,ecg,emg}.png` — ranking heatmap (4 methods × top 15 PCs)

---

## Key Observations

1. **EEG Bonferroni**: Only 2/38 PCs (PC29 and PC6) survive strict Bonferroni correction. This
   is expected given 38 simultaneous tests and the modest sample-to-class ratio. RFECV retains
   36 of 38 PCs (removes only 2 least informative), indicating the classifier benefits from most
   components.

2. **EEG CV accuracy 65.6%**: Substantially above chance (33% for 3 classes), confirming that
   the EEG PCA representation encodes phase-discriminating information.

3. **ECG/EMG low CV accuracy (36.7% / 53.9%)**: ECG essentially at chance level, consistent
   with Stage 7 ANOVA showing no significant ECG features. EMG shows moderate separability,
   driven by PC15 (Cohen's f²=0.26 — medium effect).

4. **L1 keeps almost all PCs**: For EEG all 38 PCs have non-zero L1 coefficients, suggesting
   the linear SVC does not aggressively prune the PCA space. This is expected when features
   are already orthogonal (PCA components are uncorrelated by construction).

5. **Consensus = RFE optimal**: The consensus rule (mean of 3 method ranks) selects the same
   count as the RFE optimal, since L1 and ANOVA mostly agree on direction rather than cut.

---

## Integration Points

| Stage | Connection |
|-------|------------|
| Stage 8 (Dim. Reduction) | Reads `output/stage8_dimreduction/data/{mod}_pca_reduced.csv` |
| Stage 10 (Validation)    | Reads `output/stage9_selection/data/{mod}_selected.csv` |

---

## Open Items

1. **ECG near-chance accuracy:** With n=41 observations and 3 balanced classes, a more reliable
   evaluation would require leave-one-subject-out CV rather than random stratified fold.
2. **RFE keeps most EEG PCs:** Suggests PCA components are all mildly informative; future work
   could apply sparse PCA or ICA to produce more concentrated components.
3. **No multi-modal fusion:** Selection was applied independently per modality; a joint model
   combining all three modalities may improve phase discrimination.
