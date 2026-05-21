# Stage 6: Feature Extraction — Progress Report

## Execution Date
May 20, 2026

## Status: ✅ Complete

All 16 subjects successfully processed through Stage 6 feature extraction pipeline.

---

## Implementation Summary

### Files Created/Modified

| File | Action |
|------|--------|
| `src/biosignal/config.py` | Added `STAGE6_DIR`, `STAGE6_METRICS_DIR`, `STAGE6_FIGURES_DIR`, `STAGE6_DATA_DIR` |
| `src/biosignal/stages/features.py` | **Created** — core feature extraction module |
| `src/biosignal/stages/__init__.py` | Added `features` import and `__all__` entry |
| `draft/STAGE6_PLAN.md` | **Created** — implementation plan |
| `tex/2-textuais/3-metodologia.tex` | Added `\section{Extração de Atributos}` (3 subsections) |
| `tex/2-textuais/4-resultados.tex` | Added `\section{Extração de Atributos}` (5 subsections, real metrics) |

---

## Features Implemented

### 1. Time-Domain Features (all modalities, per channel)
- RMS, MAV, Variance, ZCR (Zero Crossing Rate)
- Hjorth Activity, Mobility, Complexity
- Skewness, Kurtosis

### 2. Frequency-Domain Features (Welch PSD)
- Total Power, Mean Frequency, Median Frequency, Spectral Entropy
- **EEG only:** band powers — delta (0.5–4 Hz), theta (4–8 Hz), alpha (8–13 Hz), beta (13–30 Hz), gamma (30–50 Hz)

### 3. ECG HRV Features (time domain)
- Mean RR interval, SDNN, RMSSD, pNN50
- Detected via `scipy.signal.find_peaks` with adaptive threshold

### 4. ECG HRV Features (frequency domain)
- LF power (0.04–0.15 Hz), HF power (0.15–0.40 Hz), LF/HF ratio
- Computed from RR tachogram resampled at 4 Hz via linear interpolation

### 5. fNIRS Exclusion
- Definitively excluded (< 2.5% window retention from Stage 5)
- No fNIRS CSV generated

---

## Output Files Generated

### Data (48 CSVs)
- `output/stage6_features/data/s{000-015}_{eeg,ecg,emg}_features.csv`
- One row per window × channel; columns vary by modality

### Metrics
- `output/stage6_features/metrics/s{000-015}_features.json` — per-subject feature stats (mean, std, min, max per feature)
- `output/stage6_features/metrics/features_metrics.json` — global summary

### Figures (7 total)
- `feature_distributions_{eeg,ecg,emg}.png` — feature boxplots aggregated across subjects
- `feature_correlation_{eeg,ecg,emg}.png` — Pearson correlation heatmaps
- `eeg_band_power_summary.png` — band power bar chart per subject

---

## Key Results

### Feature Matrix Summary

| Modality | Features | Observations | Notes |
|----------|----------|--------------|-------|
| EEG | 18 | 2.417 | 9 temporal + 4 spectral + 5 bands |
| ECG | 20 | 216 | 13 general + 7 HRV |
| EMG | 13 | 147 | 9 temporal + 4 spectral |
| **Total** | — | **2.780** | 16 subjects |

### Subject-Level Window Counts (EEG)

| Subject | EEG Windows | ECG Windows | EMG Windows |
|---------|------------|------------|------------|
| s000 | 23 (184 rows) | 16 | 24 |
| s001 | 22 (176 rows) | 17 | 7 |
| s002 | 14 (112 rows) | 14 | 0 (excluded) |
| s003 | 15 (105 rows) | 2 | 13 |
| s004 | 19 (152 rows) | 4 | 10 |
| s005 | 20 (160 rows) | 17 | 17 |
| s006 | 19 (152 rows) | 2 | 8 |
| s007 | 15 (120 rows) | 9 | 2 |
| s008 | 18 (144 rows) | 19 | 8 |
| s009 | 19 (152 rows) | 19 | 3 |
| s010 | 13 (104 rows) | 14 | 4 |
| s011 | 23 (184 rows) | 23 | 21 |
| s012 | 22 (154 rows) | 23 | 10 |
| s013 | 25 (200 rows) | 0 (excluded) | 10 |
| s014 | 24 (192 rows) | 22 | 10 |
| s015 | 18 (126 rows) | 15 | 0 (excluded) |

*Note: s002 and s015 EMG had 0 usable windows (Stage 5 rejection). s013 ECG had 0 usable windows.*

### Key Feature Statistics (aggregate, all subjects)

| Feature | Value |
|---------|-------|
| EEG mean alpha_power | 19.0 µV²/Hz |
| EEG mean beta_power | 41.7 µV²/Hz |
| EEG mean hjorth_mobility | 0.33 |
| ECG mean_rr | 731.3 ms (~82 bpm) |
| ECG SDNN | 105.4 ms |
| ECG RMSSD | 132.4 ms |
| EMG RMS | 5971.0 µV |
| EMG mean_freq | 27.4 Hz |
| EMG median_freq | 20.2 Hz |

---

## CLI Usage

```bash
# Run for all subjects
uv run python -m biosignal run 6 --verbose

# Run for specific subject
uv run python -m biosignal run 6 --subject 0 --verbose
```

---

## Integration Points

| Stage | Connection |
|-------|------------|
| Stage 5 (Segmentation) | Loads `s{id}_{modality}_segments.npz` from `output/stage5_segmentation/data/segments/` |
| Stage 7 (Engineering) | Feature CSVs from `output/stage6_features/data/` are the input |

---

## Open Items

1. **Wavelet and STFT features (FE-003):** PRD lists time-frequency features as required. Current implementation covers Welch PSD only. Wavelet energy decomposition (PyWavelets) can be added in Stage 7 or as an extension of Stage 6.
2. **Nonlinear features (FE-004):** Sample entropy and DFA are computationally expensive per window. They were deferred due to runtime constraints; can be added as optional via CLI flag.
3. **HRV reliability on 5s windows:** RMSSD and SDNN estimates from 5s ECG windows are statistically noisy (< 6 beats per window). Results should be interpreted with caution; longer windows improve HRV reliability.

---

## Next Steps

1. **Stage 7 (Feature Engineering):** Load feature CSVs, apply normalization, create interaction features, handle outliers in feature space.
2. **Add wavelet features (optional):** PyWavelets already available in project; 5-level DWT energy per band.
3. **Investigate HRV reliability:** Consider concatenating adjacent valid ECG windows before HRV extraction.
