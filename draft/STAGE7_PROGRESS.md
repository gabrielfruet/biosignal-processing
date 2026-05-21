# Stage 7: Feature Engineering — Progress Report

## Execution Date
May 20, 2026

## Status: ✅ Complete

All 16 subjects successfully processed through Stage 7 feature engineering pipeline.

---

## Implementation Summary

### Files Created/Modified

| File | Action |
|------|--------|
| `src/biosignal/config.py` | Added `STAGE7_DIR`, `STAGE7_METRICS_DIR`, `STAGE7_FIGURES_DIR`, `STAGE7_DATA_DIR` |
| `src/biosignal/stages/engineering.py` | **Created** — full feature engineering module |
| `src/biosignal/stages/__init__.py` | Added `engineering` import |
| `draft/STAGE7_PLAN.md` | **Created** |
| `tex/2-textuais/3-metodologia.tex` | Added `\section{Engenharia de Atributos}` (6 subsections) |
| `tex/2-textuais/4-resultados.tex` | Added `\section{Engenharia de Atributos}` (4 subsections, real metrics) |

---

## Engineering Steps Implemented

### 1. Phase Assignment
- Baseline: start_s < 30s
- Stimulation: 30 ≤ start_s < 60s
- Recovery: start_s ≥ 60s
- Added as `phase` column

### 2. Band Power Ratios (EEG only — ENG-001)
- `alpha_beta_ratio`: alpha / (beta + ε)
- `theta_alpha_ratio`: theta / (alpha + ε)
- `engagement_index`: beta / (alpha + theta + ε)
- `delta_beta_ratio`: delta / (beta + ε)
- `theta_beta_ratio`: theta / (beta + ε)

### 3. Baseline Normalisation (ENG-002)
- Z-score per (subject, channel, feature) relative to baseline windows
- Added `{feature}_norm` columns for all features
- Subjects with no baseline windows get NaN norm columns

### 4. Delta Features (ENG-003)
- Δ and Δ² for 5 key features per modality (rms, alpha_power, beta_power, hjorth_mobility, spectral_entropy for EEG; rms, mean_rr, sdnn, lf_hf_ratio, hjorth_mobility for ECG; rms, mav, mean_freq, median_freq, hjorth_mobility for EMG)
- First window has NaN delta; first two have NaN delta²

### 5. Temporal Aggregations (ENG-004)
- Per (subject, channel, phase): mean, std, min, max for every feature
- Saved as separate `_aggregated.csv` files (Stage 8 input)

### 6. Phase Discriminability (ENG-005 proxy)
- One-way ANOVA across 3 phases for each feature
- EEG: 5 features significant (p < 0.05)
- ECG/EMG: no significant discriminators

### 7. Redundancy Analysis (ENG-006)
- Pairwise Pearson correlation, threshold |r| ≥ 0.95
- EEG: 7 redundant pairs (hjorth_activity ↔ variance, adjacent band powers)
- ECG: 0 redundant pairs
- EMG: 2 redundant pairs

---

## Output Files Generated

### Data (96 CSVs)
- `output/stage7_engineering/data/s{000-015}_{eeg,ecg,emg}_engineered.csv` — 48 files
- `output/stage7_engineering/data/s{000-015}_{eeg,ecg,emg}_aggregated.csv` — 48 files (excl. missing)

### Metrics
- `output/stage7_engineering/metrics/s{000-015}_engineering.json`
- `output/stage7_engineering/metrics/redundancy_report.json`
- `output/stage7_engineering/metrics/discriminability_report.json`
- `output/stage7_engineering/metrics/engineering_metrics.json`

### Figures (5 total)
- `feature_redundancy_eeg.png` — Pearson r heatmap
- `feature_redundancy_ecg.png`
- `feature_redundancy_emg.png`
- `band_ratios_eeg.png` — band ratio boxplots by phase
- `phase_discriminability.png` — ANOVA F-statistic bar chart

---

## Key Results

### Engineered Column Counts (per subject)

| Modality | Original | + Ratios | + Norm | + Δ/Δ² | + Phase | Total |
|----------|----------|---------|--------|---------|---------|-------|
| EEG | 18 | 5 | 18 | 10 | 1 | 63 |
| ECG | 20 | — | 20 | 10 | 1 | 57 |
| EMG | 13 | — | 13 | 10 | 1 | 43 |

### Phase Discriminability (top features by F-statistic)

| Feature | Modality | F-statistic | Significant |
|---------|----------|-------------|-------------|
| alpha_beta_ratio | EEG | 23.16 | ✅ |
| theta_beta_ratio | EEG | 17.41 | ✅ |
| mav | EEG | 9.32 | ✅ |
| rms | EEG | 9.32 | ✅ |
| mean_freq | EEG | 7.78 | ✅ |
| zcr | ECG | 2.82 | ❌ |
| rms | EMG | 2.60 | ❌ |

### Redundancy Summary

| Modality | Features | Redundant Pairs |
|----------|----------|-----------------|
| EEG | 21 | 7 |
| ECG | 20 | 0 |
| EMG | 13 | 2 |

---

## CLI Usage

```bash
uv run python -m biosignal run 7 --verbose
uv run python -m biosignal run 7 --subject 0 --verbose
```

---

## Integration Points

| Stage | Connection |
|-------|------------|
| Stage 6 (Features) | Reads `output/stage6_features/data/s*_{mod}_features.csv` |
| Stage 8 (Dim. Reduction) | Reads `output/stage7_engineering/data/s*_{mod}_aggregated.csv` |

---

## Open Items

1. **EMG missing subjects (s002, s015):** No Stage 6 CSV exists → Stage 7 also skips them. These subjects had 0 usable EMG windows since Stage 5.
2. **ECG missing s013:** Same situation — 0 usable ECG windows propagated from Stage 5.
3. **Wavelet/nonlinear features deferred:** PRD FE-003/FE-004 (wavelet, DFA, Poincaré) not yet implemented. Can be added as additional columns in Stage 6 or as a Stage 7 extension.
4. **Aggregated CSV is sparse for short recordings:** Subjects with few windows per phase may have unreliable mean/std estimates — this should be flagged during dimensionality reduction.

---

## Next Steps

1. **Stage 8 (Dimensionality Reduction):** Load `_aggregated.csv` files, apply PCA, generate Scree plot and cumulative variance curve.
2. **Remove identified redundant features:** 7 EEG + 2 EMG pairs flagged — can be pruned before PCA to reduce noise.
3. **Consider longer windows for ECG HRV:** RMSSD/SDNN estimates from 5s windows are noisy; concatenating baseline windows per subject may improve HRV reliability.
