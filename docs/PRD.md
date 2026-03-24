# PRD: Biosignal Processing Pipeline

## 1. Overview

**Project Name:** BioSignal-Process
**Type:** Scientific Data Processing Pipeline (Coursework)
**Core Functionality:** Transform raw biosignal data (ECG, EMG, EEG, PPG, GSR, Respiratory) into a validated, feature-rich dataset ready for pattern recognition and machine learning.
**Target Users:** Students, researchers in biomedical engineering.

---

## 2. Goals & Objectives

| Goal | Description |
|------|-------------|
| **Signal Integrity** | Guarantee physical and physiological signal integrity from acquisition |
| **Quality Assurance** | Automate signal quality evaluation using SQI metrics |
| **Statistical Rigor** | Ensure statistical validity at each processing stage |
| **Reproducibility** | Fully documented, version-controlled pipeline |
| **Deliverable Readiness** | Produce dataset ready for ML/RP + technical report |

---

## 3. Scope

### 3.1 Biosignal Types Supported

- ECG (Electrocardiogram)
- EMG (Electromyogram)
- EEG (Electroencephalogram)
- PPG (Photoplethysmogram)
- GSR (Galvanic Skin Response)
- Respiratory signals

### 3.2 Processing Pipeline Stages

| Stage | Name | Priority |
|-------|------|----------|
| 1 | Biosignal Acquisition | Required |
| 2 | Signal Quality Index (SQI) | Required |
| 3 | Initial Statistical Analysis | Required |
| 4 | Data Cleaning & Correction | Required |
| 5 | Segmentation (Windowing) | Required |
| 6 | Feature Extraction | Required |
| 7 | Feature Engineering | Required |
| 8 | Dimensionality Reduction | Required |
| 9 | Feature Selection | Required |
| 10 | Final Statistical Validation | Required |

---

## 4. Requirements by Stage

### Stage 1: Biosignal Acquisition

| Req ID | Requirement |
|--------|-------------|
| ACQ-001 | Sample rate must follow Nyquist theorem |
| ACQ-002 | Define experimental protocols (position, duration, conditions) |
| ACQ-003 | Document hardware/sensor specifications |
| ACQ-004 | Record acquisition environment details |
| ACQ-005 | Generate raw signal visualizations |

**Deliverable 1:**
- Technical PDF (2-3 pages)
- Raw data (.csv/.mat format)
- Raw signal plot with problem identification

---

### Stage 2: Signal Quality Index (SQI)

| Req ID | Requirement |
|--------|-------------|
| SQI-001 | Calculate Signal-to-Noise Ratio (SNR) |
| SQI-002 | Compute Kurtosis and Skewness |
| SQI-003 | Calculate Spectral Entropy |
| SQI-004 | Detect artifacts (movement, loose electrode) |
| SQI-005 | Implement automatic segment rejection |
| SQI-006 | Differentiate physiological vs instrumental outliers |

**Deliverable 2:**
- `metrics/sqi_metrics.json`
- Comparative plots (good × bad segments)
- Marked rejected segments

---

### Stage 3: Initial Statistical Analysis

| Req ID | Requirement |
|--------|-------------|
| STA-001 | Compute descriptive statistics (mean, median, variance, SD) |
| STA-002 | Calculate quartiles and IQR |
| STA-003 | Generate histograms and boxplots |
| STA-004 | Apply normality tests (Shapiro-Wilk, Kolmogorov-Smirnov) |
| STA-005 | Apply homoscedasticity tests (Levene, Bartlett) |
| STA-006 | Generate Q-Q plots |
| STA-007 | Compute correlation matrix with heatmap |

**Deliverable 3:**
- `metrics/statistics.json` with all test results
- All visualizations (histograms, boxplots, Q-Q, heatmap)
- Interpretation text

---

### Stage 4: Data Cleaning & Correction

| Req ID | Requirement |
|--------|-------------|
| CLEAN-001 | Apply notch filter (50/60 Hz) |
| CLEAN-002 | Apply signal-specific band-pass filter |
| CLEAN-003 | Interpolate short data gaps |
| CLEAN-004 | Apply Winsorization for extreme outliers |
| CLEAN-005 | Implement z-score or MAD-based rejection |
| CLEAN-006 | Validate with before/after statistical comparison |
| CLEAN-007 | Calculate effect size (Cohen's d) |

**Deliverable 4:**
- Before/after signal comparison plots
- `metrics/cleaning_validation.json`
- Effect size results

---

### Stage 5: Segmentation (Windowing)

| Req ID | Requirement |
|--------|-------------|
| SEG-001 | Implement fixed window segmentation (1s, 5s options) |
| SEG-002 | Support overlapping windows |
| SEG-003 | Support event-based physiological segmentation |
| SEG-004 | Validate intra-window stability |
| SEG-005 | Analyze inter-window variance |

**Deliverable 5:**
- Segmentation strategy documentation
- Window stability visualizations
- `metrics/segmentation_metrics.json`

---

### Stage 6: Feature Extraction

| Req ID | Requirement |
|--------|-------------|
| FE-001 | Extract time-domain features (RMS, MAV, Variance, ZCR, Hjorth) |
| FE-002 | Extract frequency-domain features (FFT, spectral power, band power) |
| FE-003 | Extract time-frequency features (Wavelet, STFT, Hilbert-Huang) |
| FE-004 | Extract nonlinear features (Entropy, DFA, Fractal dimension, Poincaré) |
| FE-005 | Organize features by domain category |

**Deliverable 6:**
- `data/features.csv`
- Feature documentation table
- Explanatory graphics

---

### Stage 7: Feature Engineering

| Req ID | Requirement |
|--------|-------------|
| ENG-001 | Create band power ratios |
| ENG-002 | Normalize features by baseline |
| ENG-003 | Generate derived features (Δ, Δ²) |
| ENG-004 | Implement temporal aggregations |
| ENG-005 | Validate correlation with response variable |
| ENG-006 | Analyze feature redundancy |

**Deliverable 7:**
- `data/features_engineered.csv`
- `metrics/feature_correlations.json`
- Redundancy report

---

### Stage 8: Dimensionality Reduction

| Req ID | Requirement |
|--------|-------------|
| DR-001 | Apply PCA with explained variance analysis |
| DR-002 | Apply ICA for source separation |
| DR-003 | Generate Scree plot |
| DR-004 | Calculate cumulative variance |
| DR-005 | Validate with feature reconstruction |

**Deliverable 8:**
- `metrics/pca_results.json`
- Scree plot + cumulative variance graph
- Reconstruction error report

---

### Stage 9: Feature Selection

| Req ID | Requirement |
|--------|-------------|
| SEL-001 | Implement Filter methods (ANOVA, Mutual Information, ReliefF) |
| SEL-002 | Implement Wrapper methods (Sequential Forward/Backward) |
| SEL-003 | Implement Embedded methods (LASSO) |
| SEL-004 | Generate feature ranking |
| SEL-005 | Apply multiple comparison corrections (Bonferroni/FDR) |
| SEL-006 | Calculate effect size per feature |

**Deliverable 9:**
- `metrics/feature_ranking.json`
- Final feature selection table
- Statistical test results with corrections

---

### Stage 10: Final Statistical Validation

| Req ID | Requirement |
|--------|-------------|
| VAL-001 | Check multicollinearity (VIF) |
| VAL-002 | Analyze class statistical separability |
| VAL-003 | Evaluate class balance |
| VAL-004 | Generate class density curves |
| VAL-005 | Confirm dataset readiness for RP |

**Deliverable 10:**
- `metrics/final_validation.json`
- Density curves by class
- `data/dataset_final.csv`

---

## 5. Acceptance Criteria

- [ ] All 10 pipeline stages implemented in `src/`
- [ ] All metrics saved as JSON
- [ ] All visualizations saved to `output/figures/`
- [ ] Pipeline is reproducible (deterministic where possible)
- [ ] Final dataset passes VIF, separability, and balance checks
- [ ] Technical-scientific report in TCC format
- [ ] Dataset ready for SVM, kNN, RF, NN, CNN applications

---

## 6. Deliverables Summary

| # | Deliverable | Format |
|---|-------------|--------|
| 1 | Biosignal Acquisition Report | PDF + raw data |
| 2 | SQI Evaluation | `metrics/sqi_metrics.json` + plots |
| 3 | Initial Statistical Analysis | `metrics/statistics.json` + plots |
| 4 | Cleaning Validation | `metrics/cleaning_validation.json` + plots |
| 5 | Segmentation Strategy | `metrics/segmentation_metrics.json` + plots |
| 6 | Feature Extraction | `data/features.csv` |
| 7 | Feature Engineering | `data/features_engineered.csv` + correlations |
| 8 | Dimensionality Reduction | `metrics/pca_results.json` + plots |
| 9 | Feature Selection | `metrics/feature_ranking.json` |
| 10 | Final Validated Dataset | `data/dataset_final.csv` + `metrics/final_validation.json` |
| **Final** | Integrative Technical-Scientific Report | TCC (LaTeX/Overleaf) |
