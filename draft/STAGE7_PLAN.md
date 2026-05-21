# Stage 7: Feature Engineering — Implementation Plan

## 1. Requirements Summary

From PRD.md Stage 7 requirements:

| Req ID | Requirement |
|--------|-------------|
| ENG-001 | Create band power ratios |
| ENG-002 | Normalize features by baseline |
| ENG-003 | Generate derived features (Δ, Δ²) |
| ENG-004 | Implement temporal aggregations |
| ENG-005 | Validate correlation with response variable |
| ENG-006 | Analyze feature redundancy |

**Deliverable 7:**
- `data/s{id}_{modality}_engineered.csv` — enriched feature matrix
- `data/s{id}_{modality}_aggregated.csv` — temporal aggregations
- `metrics/redundancy_report.json`
- `metrics/engineering_metrics.json`

---

## 2. Phase Assignment

Based on experimental protocol (baseline 30s → stimulation 30s → recovery):

| Phase | Window start_s range |
|-------|----------------------|
| baseline | start_s < 30 |
| stimulation | 30 ≤ start_s < 60 |
| recovery | start_s ≥ 60 |

Windows are assigned a `phase` column before any other engineering step.

---

## 3. Engineering Steps

### 3.1 Band Power Ratios (EEG only — ENG-001)

Computed per window × channel from existing band powers:

| Feature | Formula | Interpretation |
|---------|---------|----------------|
| `alpha_beta_ratio` | alpha / (beta + ε) | Relaxation vs. alertness |
| `theta_alpha_ratio` | theta / (alpha + ε) | Cognitive load proxy |
| `engagement_index` | beta / (alpha + theta + ε) | Cortical engagement |
| `delta_beta_ratio` | delta / (beta + ε) | Sleep vs. active |
| `theta_beta_ratio` | theta / (beta + ε) | Anxiety/stress proxy |

### 3.2 Baseline Normalization (ENG-002)

For each (subject, channel, feature):
1. Compute baseline mean and std from windows where `phase == 'baseline'`
2. Apply z-score normalization across all windows:
   `feature_norm = (x − baseline_mean) / (baseline_std + ε)`
3. Appended as new columns: `{feature}_norm`
4. If no baseline windows exist for a subject, mark norms as NaN

### 3.3 Delta Features (ENG-003)

For each (subject, channel) sorted by `window_id`:
- `delta_{feature}` = diff between consecutive windows (NaN for first)
- `delta2_{feature}` = diff of delta (NaN for first two)

Computed for the 5 most informative features per modality (to avoid excessive column explosion):
- EEG: rms, alpha_power, beta_power, hjorth_mobility, spectral_entropy
- ECG: rms, mean_rr, sdnn, lf_hf_ratio, hjorth_mobility
- EMG: rms, mav, mean_freq, median_freq, hjorth_mobility

### 3.4 Temporal Aggregations (ENG-004)

Two aggregation levels:
1. **Global (all windows):** mean, std, min, max per (subject, channel, feature)
2. **Per-phase:** mean per (subject, channel, feature, phase)

Output: `s{id}_{modality}_aggregated.csv` — one row per (subject, channel, phase)

### 3.5 Phase Discriminability (ENG-005 proxy)

No explicit emotion labels exist → use protocol phase (baseline/stimulation/recovery) as response variable.

For each feature:
- One-way ANOVA across the 3 phases (using `scipy.stats.f_oneway`)
- Report F-statistic and p-value
- Rank features by F-statistic (higher = more discriminating between phases)

### 3.6 Feature Redundancy (ENG-006)

For each modality:
- Pairwise Pearson correlation matrix across all features (aggregated across all subjects)
- Flag pairs with |r| > 0.95 as highly correlated / redundant
- Output JSON + heatmap figure

---

## 4. Output Structure

```
output/stage7_engineering/
├── data/
│   ├── s{id}_{modality}_engineered.csv   # original + ratios + norm + deltas
│   └── s{id}_{modality}_aggregated.csv   # temporal aggregations (Stage 8 input)
├── metrics/
│   ├── s{id}_engineering.json
│   ├── redundancy_report.json
│   ├── discriminability_report.json
│   └── engineering_metrics.json
└── figures/
    ├── feature_redundancy_eeg.png
    ├── feature_redundancy_ecg.png
    ├── feature_redundancy_emg.png
    ├── band_ratios_eeg.png
    └── phase_discriminability.png
```

### Engineered CSV Additional Columns

Beyond Stage 6 columns, per modality:

| Column | Modalities |
|--------|-----------|
| `phase` | all |
| `alpha_beta_ratio`, `theta_alpha_ratio`, `engagement_index`, `delta_beta_ratio`, `theta_beta_ratio` | EEG |
| `{feature}_norm` | all (baseline-normalized) |
| `delta_{feature}`, `delta2_{feature}` | all (5 features per modality) |

---

## 5. Configuration Constants (config.py)

```python
STAGE7_DIR = OUTPUT_DIR / "stage7_engineering"
STAGE7_METRICS_DIR = STAGE7_DIR / "metrics"
STAGE7_FIGURES_DIR = STAGE7_DIR / "figures"
STAGE7_DATA_DIR = STAGE7_DIR / "data"
```

---

## 6. Dependencies

All already available:
- `numpy`, `pandas`, `scipy`, `matplotlib`

---

## 7. Execution

```bash
uv run python -m biosignal run 7 --subject 0 --verbose  # validate
uv run python -m biosignal run 7 --verbose               # all subjects
```

---

## 8. Integration Points

- **Input:** `output/stage6_features/data/s*_{eeg,ecg,emg}_features.csv`
- **Output:** Aggregated CSVs for Stage 8 (PCA / dimensionality reduction)

---

## 9. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Engineered CSV per subject per modality | `ls output/stage7_engineering/data/` |
| 2 | `phase` column present | Check CSV columns |
| 3 | Band ratios in EEG CSV | `alpha_beta_ratio` column exists |
| 4 | `_norm` columns present | Check CSV columns |
| 5 | Delta columns present | `delta_rms` exists |
| 6 | Aggregated CSV per subject per modality | Separate `_aggregated.csv` |
| 7 | Redundancy report JSON saved | `redundancy_report.json` |
| 8 | Phase discriminability report saved | `discriminability_report.json` |
| 9 | 5 figures generated | `ls output/stage7_engineering/figures/` |
| 10 | CLI command works | `uv run python -m biosignal run 7` |
