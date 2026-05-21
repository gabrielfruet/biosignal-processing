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
| 2 | Signal Quality Index (SQI) | ✅ Complete | SNR, kurtosis, spectral entropy, artifact detection |
| 3 | Initial Statistical Analysis | ✅ Complete | Descriptive stats, normality tests, correlation heatmap |
| 4 | Data Cleaning & Correction | ✅ Complete | Notch filter, band-pass, interpolation, Winsorization, Cohen's d |
| 5 | Segmentation | ✅ Complete | Fixed/overlapping windows, SQI propagation, 64 NPZ files |
| 6 | Feature Extraction | ✅ Complete | 2.780 feature rows, 18/20/13 features per modality |
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

### Stage 2: SQI ✅
- **Executed:** April 16, 2026
- **Output:** `output/metrics/sqi_metrics.json` + per-subject SQI files + `sqi_heatmap.png`
- **Key findings:**
  - 5-second window segmentation
  - EEG: 3.8-17.9% rejection rates
  - ECG: highly variable (5-100% depending on subject)
  - EMG: 5-100% rejection
  - fNIRS: 85-100% rejection (expected due to low SNR nature)

### Stage 3: Statistics ✅
- **Executed:** April 16, 2026
- **Output:** `output/metrics/statistics.json` + per-subject statistics + visualizations
- **Key findings:**
  - 16 subjects, 192 channels analyzed
  - 0/192 channels passed normality test (expected for biosignals)
  - 0/32 modality-channel groups showed homoscedasticity
  - All biosignals deviated from normal distribution

### Stage 4: Cleaning ✅
- **Executed:** April 16, 2026
- **Output:** `output/metrics/cleaning_validation.json` + per-subject cleaning metrics + visualizations
- **Applied:**
  - Notch filter (50 Hz) for powerline removal
  - Band-pass filters (modality-specific)
  - Gap interpolation (linear, <1s gaps)
  - Winsorization (5th-95th percentile)
  - Z-score outlier rejection

### Stage 5: Segmentation ✅
- **Completed:** May 6, 2026
- **Output:** 64 NPZ segment files (`output/stage5_segmentation/data/segments/`)
- **Key findings:**
  - EEG: 93.9% window retention, CV < 2%
  - ECG: 64.7% retention, 97.7% ADF stationary
  - EMG: 44.0% retention (movement artifacts)
  - fNIRS: 2.5% retention — definitively excluded

### Stage 6: Feature Extraction ✅
- **Completed:** May 20, 2026
- **Output:** 48 CSV files + 7 figures (`output/stage6_features/`)
- **Key findings:**
  - 2,780 total feature rows (EEG: 2,417 | ECG: 216 | EMG: 147)
  - EEG: 18 features/channel (9 temporal + 4 spectral + 5 band powers)
  - ECG: 20 features/channel (13 general + 7 HRV)
  - EMG: 13 features/channel (9 temporal + 4 spectral)
  - EEG dominant band: beta (41.7 µV²/Hz), ECG mean RR: 731 ms

---

## Next Steps

### Immediate (Stage 7)
1. Implement Stage 7: Feature Engineering
2. Input: `output/stage6_features/data/s*_{eeg,ecg,emg}_features.csv`

### Stage 7 Requirements
- Band power ratios (alpha/beta, theta/alpha, etc.)
- Normalize features by baseline window
- Generate delta features (Δ, Δ²)
- Temporal aggregations (mean/std/min/max per subject per modality)
- Feature redundancy analysis
- Correlation with response variable

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