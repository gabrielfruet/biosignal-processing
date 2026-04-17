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

---

## Next Steps

### Immediate (Stage 5)
1. Implement Stage 5: Segmentation (Windowing)
2. Add SQI-based segment rejection to cleaning stage

### Stage 5 Requirements
- Fixed window segmentation (1s, 5s options)
- Overlapping windows support
- Event-based physiological segmentation
- Intra-window stability validation
- Inter-window variance analysis

### Stage 6 Requirements
- Time-domain features (RMS, MAV, Variance, ZCR, Hjorth)
- Frequency-domain features (FFT, spectral power, band power)
- Time-frequency features (Wavelet, STFT, Hilbert-Huang)
- Nonlinear features (Entropy, DFA, Fractal dimension, Poincaré)

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