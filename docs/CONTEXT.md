# Biosignal Processing Pipeline - Project Context

## Overview

**Project Name:** BioSignal-Process
**Dataset:** IEEE Multimodal Emotion Recognition Dataset
**Goal:** Transform raw biosignal data into a validated, feature-rich dataset ready for machine learning

---

## Dataset Summary

| Property | Value |
|----------|-------|
| **Subjects** | 16 (s000-s015) |
| **Task** | Emotion induction protocol |
| **Intervals** | Baseline (30s) → Stimulation (30s) → Recovery |
| **Total Duration** | 60 seconds per subject |

### Modalities

| Modality | Channels | Sampling Rate | System |
|----------|----------|---------------|--------|
| EEG | 8 | 512 Hz | Emotiv EPOC+ |
| ECG | 1 | 250 Hz | - |
| EMG | 1 | 250 Hz | - |
| fNIRS | 2 (HbO, HbR) | 16 Hz | Beer-Lambert law |

---

## Pipeline Stages

| Stage | Name | Status | Key Deliverables |
|-------|------|--------|------------------|
| 1 | Biosignal Acquisition | ✅ Complete | Raw signals, metadata, Nyquist validation |
| 2 | Signal Quality Index (SQI) | 🔄 Execute | SNR, kurtosis, spectral entropy, artifact detection |
| 3 | Initial Statistical Analysis | 🔄 Execute | Descriptive stats, normality tests, correlation heatmap |
| 4 | Data Cleaning & Correction | 📋 Next | Notch filter, band-pass, interpolation, Winsorization |
| 5 | Segmentation | 📋 Todo | Fixed/overlapping windows, event-based |
| 6 | Feature Extraction | 📋 Todo | Time/frequency/time-frequency/nonlinear features |
| 7 | Feature Engineering | 📋 Todo | Band ratios, normalization, derived features |
| 8 | Dimensionality Reduction | 📋 Todo | PCA, ICA, Scree plot |
| 9 | Feature Selection | 📋 Todo | Filter/Wrapper/Embedded methods |
| 10 | Final Validation | 📋 Todo | VIF, separability, class balance |

---

## Current Progress

### Stage 1: Acquisition ✅
- **Completed:** March 24, 2025
- **Metrics saved:** `output/metrics/s000-s015_acquisition.json`, `acquisition_summary.json`
- **Figures saved:** 16 subject raw signal plots + overview (16 subjects × 4 modalities)
- **Key findings:**
  - 16/16 subjects have detected signal problems
  - 32 flat channels detected
  - 6 clipping channels detected
  - 16 noisy channels detected
  - All subjects have flat EEG channels (likely dry EEG system characteristic)

### Stage 2: SQI ⚠️
- **Status:** Code implemented (`src/biosignal/stages/sqi.py`)
- **Pending execution:** Run to generate `output/metrics/sqi_metrics.json`
- **Key features:**
  - 5-second window segmentation
  - SNR, kurtosis, skewness, spectral entropy computation
  - Artifact detection (movement, loose electrode)
  - Per-modality rejection thresholds
  - Good vs bad segment comparison plots
  - Global SQI heatmap

### Stage 3: Statistics ⚠️
- **Status:** Code implemented (`src/biosignal/stages/statistics.py`)
- **Pending execution:** Run to generate `output/metrics/statistics.json`
- **Key features:**
  - Descriptive statistics (mean, median, variance, SD, skewness, kurtosis)
  - Quartiles and IQR
  - Normality tests (Shapiro-Wilk, Kolmogorov-Smirnov)
  - Homoscedasticity tests (Levene, Bartlett)
  - Visualizations: histograms, boxplots, Q-Q plots, correlation heatmaps

---

## Next Steps

### Immediate (Stage 4)
1. Execute Stage 2 (SQI): `uv run python -m biosignal run 2 --verbose`
2. Execute Stage 3 (Statistics): `uv run python -m biosignal run 3 --verbose`
3. Implement Stage 4: Data Cleaning & Correction

### Stage 4 Requirements
- Notch filter (50/60 Hz powerline removal)
- Signal-specific band-pass filter
- Interpolate short data gaps
- Winsorization for extreme outliers
- Z-score or MAD-based rejection
- Before/after statistical comparison
- Cohen's d effect size calculation

---

## Project Structure

```
biosignal_processing/
├── src/biosignal/
│   ├── __init__.py
│   ├── config.py
│   ├── cli.py
│   ├── io/ieee.py
│   └── stages/
│       ├── acquisition.py    ✅ Stage 1
│       ├── sqi.py            ⚠️ Stage 2 (code ready)
│       ├── statistics.py     ⚠️ Stage 3 (code ready)
│       ├── cleaning.py      📋 Stage 4 (to implement)
│       ├── segmentation.py   📋 Stage 5
│       ├── features.py       📋 Stage 6
│       ├── engineering.py    📋 Stage 7
│       ├── dimreduction.py   📋 Stage 8
│       ├── selection.py      📋 Stage 9
│       └── validation.py     📋 Stage 10
├── output/
│   ├── metrics/              # JSON metrics per stage
│   ├── figures/             # PNG visualizations
│   └── data/                # Processed datasets
└── docs/                    # Documentation
```

---

## Configuration

Key parameters in `src/biosignal/config.py`:
- `SFREQ`: Sampling frequencies per modality
- `CHANNELS`: Channel names per modality
- `NYQUIST_MAX_FREQ`: Nyquist validation limits
- Output directories: `METRICS_DIR`, `FIGURES_DIR`, `DATA_OUT_DIR`