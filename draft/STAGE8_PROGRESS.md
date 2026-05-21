# Stage 8: Dimensionality Reduction — Progress Report

## Execution Date
May 21, 2026

## Status: ✅ Complete

All 3 modalities processed. PCA applied with NaN-aware pre-processing and StandardScaler.

---

## Implementation Summary

### Files Created/Modified

| File | Action |
|------|--------|
| `src/biosignal/config.py` | Added `STAGE8_DIR`, `STAGE8_METRICS_DIR`, `STAGE8_FIGURES_DIR`, `STAGE8_DATA_DIR` |
| `src/biosignal/stages/dimreduction.py` | **Created** — full PCA module |
| `src/biosignal/stages/__init__.py` | Added `dimreduction` import |
| `pyproject.toml` | Added `scikit-learn>=1.8` dependency (auto-added via `uv add`) |

---

## Input Data (from Stage 7)

| Modality | Subjects | Observations | Feature Columns | NaN-dropped |
|----------|----------|--------------|-----------------|-------------|
| EEG      | 16       | 375          | 224 → 220       | 4 (zcr_norm)   |
| ECG      | 15       | 41           | 200 → 172       | 28 (lf/hf NaN + zcr_norm) |
| EMG      | 14       | 37           | 144 → 140       | 4 (zcr_norm)   |

ECG had 24 lf/hf-related columns dropped (lf_power, hf_power, lf_hf_ratio and their norm/delta 
variants), confirming the spectral HRV limitation identified in Stage 6.

---

## PCA Results

| Modality | Obs | Features | PC@90% | PC@95% | Var@PC1 | Var@PC2 | Var@5PCs | Var@10PCs |
|----------|-----|----------|--------|--------|---------|---------|----------|-----------|
| EEG      | 375 | 220      | 26     | 38     | 18.7%   | 15.7%   | 54.0%    | 71.1%     |
| ECG      | 41  | 172      | 18     | 22     | 17.9%   | 11.3%   | 53.2%    | 76.2%     |
| EMG      | 37  | 140      | 15     | 18     | 18.9%   | 16.1%   | 61.6%    | 80.9%     |

Compression ratio at 95% threshold:
- EEG: 220 → 38 components (83% reduction)
- ECG: 172 → 22 components (87% reduction)
- EMG: 140 → 18 components (87% reduction)

---

## Top PC1 Loadings

### EEG
Features driving PC1 are delta-features of spectral power variability:
- `delta2_alpha_power_std` (0.130), `delta2_alpha_power_max` (0.130)
- `delta2_beta_power_std` (0.128), `delta_beta_power_std` (0.128)
- `alpha_power_std` (0.127)

### EEG PC2
Driven by normalised power in the _max aggregation:
- `total_power_norm_max` (0.151), `theta_power_norm_max` (0.149)
- `hjorth_complexity_norm_max` (0.149), `theta_beta_ratio_norm_max` (0.149)

### ECG PC1
Driven by Hjorth mobility variability (delta features):
- `hjorth_mobility_std` (0.167), `delta2_hjorth_mobility_max` (0.165)
- `delta_hjorth_mobility_std` (0.165)

---

## Output Files

### Data (6 CSVs)
- `output/stage8_dimreduction/data/{eeg,ecg,emg}_pca_reduced.csv` — reduced component scores
- `output/stage8_dimreduction/data/{eeg,ecg,emg}_pca_loadings.csv` — component loadings matrix

### Metrics (4 JSONs)
- `output/stage8_dimreduction/metrics/{eeg,ecg,emg}_pca_metrics.json`
- `output/stage8_dimreduction/metrics/dimreduction_metrics.json`

### Figures (12 PNGs)
- `scree_plot_{eeg,ecg,emg}.png` — explained variance per component
- `cumulative_variance_{eeg,ecg,emg}.png` — cumulative variance with 90/95% lines
- `pca_scatter_{eeg,ecg,emg}.png` — PC1×PC2 scatter coloured by phase
- `pca_loadings_{eeg,ecg,emg}.png` — loadings heatmap (top 15 features × PC1–PC5)

---

## Key Observations

1. **High dimensionality vs samples:** ECG (41 obs, 172 features) and EMG (37 obs, 140 features)
   are severely underdetermined. PCA is bounded to min(n_obs, n_features) components = n_obs,
   so the full decomposition uses all 41/37 components; the 95% threshold selects 22/18.

2. **EEG PC1 captures spectral dynamics:** The highest-loading features for EEG PC1 are
   second-order delta features (Δ² of alpha/beta power), suggesting the primary source of
   variance across (channel, phase) observations is temporal non-stationarity of spectral power.

3. **ECG NaN cascade:** 28 of 200 ECG feature columns were dropped (all lf_power, hf_power,
   lf_hf_ratio variants), consistent with 5s window HRV spectral limitation from Stage 6.

4. **Phase separation in 2D PCA scatter:** Visual inspection of scatter plots shows partial
   clustering by phase for EEG, less so for ECG/EMG, consistent with Stage 7 ANOVA results.

---

## Integration Points

| Stage | Connection |
|-------|------------|
| Stage 7 (Engineering) | Reads `output/stage7_engineering/data/s*_{mod}_aggregated.csv` |
| Stage 9 (Selection)   | Reads `output/stage8_dimreduction/data/{mod}_pca_reduced.csv` |

---

## Open Items

1. **ECG/EMG sample size:** n=41 and n=37 observations are very low for PCA stability.
   Results should be interpreted cautiously; bootstrap or cross-validated PCA would be more robust.
2. **Unified cross-modal PCA:** Current approach applies PCA independently per modality.
   A joint PCA or CCA (Canonical Correlation Analysis) across modalities could reveal inter-modal
   structure for Stage 9.
3. **t-SNE/UMAP visualisation:** For publication-quality exploratory plots, non-linear projections
   may reveal class structure more clearly than linear PCA scatter.
