# Stage 4: Data Cleaning & Correction - Implementation Plan

## 1. Requirements Summary

From PRD.md Stage 4 requirements:

| Req ID | Requirement |
|--------|-------------|
| CLEAN-001 | Apply notch filter (50/60 Hz powerline noise removal) |
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

## 2. Modality-Specific Filter Specifications

### EEG
- **Band-pass:** 0.5-50 Hz (preserves delta, theta, alpha, beta bands)
- **Notch:** 50/60 Hz (powerline interference)
- **Filter type:** Butterworth IIR (order 4)

### ECG
- **Band-pass:** 0.5-50 Hz (QRS complex, T-wave range)
- **Notch:** 50/60 Hz
- **Filter type:** Butterworth IIR (order 4)

### EMG
- **Band-pass:** 20-250 Hz (muscle activity range)
- **Notch:** 50/60 Hz
- **Filter type:** Butterworth IIR (order 4)

### fNIRS
- **Band-pass:** 0.01-0.1 Hz (hemodynamic oscillations)
- **Filter type:** Butterworth IIR (order 2, due to low frequency requirements)

---

## 3. Implementation Strategy

### 3.1 Filter Pipeline

```
Raw Signal → Notch Filter → Band-Pass Filter → Clean Signal
```

### 3.2 Gap Interpolation
- Detect gaps using derivative threshold (>50 samples with no change)
- Interpolate gaps < 1 second using linear interpolation
- Mark gaps > 1 second as bad segments (handled by SQI)

### 3.3 Outlier Handling (Winsorization)
- **Method:** Replace values beyond percentile limits
- **Default:** 5th and 95th percentiles
- **Configurable** via threshold parameter

### 3.4 Z-score / MAD Rejection
- **Z-score:** Reject samples where |z| > 3 (configurable)
- **MAD (Median Absolute Deviation):** Reject where MAD > 3.5 * median
- **Window-based:** Apply per-segment for stability

---

## 4. Validation Strategy

### 4.1 Before/After Comparison
- Save filtered signal alongside original
- Compute same descriptive statistics as Stage 3
- Generate comparison visualizations:
  - Overlay plot (before/after)
  - Spectral density comparison
  - Distribution comparison (histogram)

### 4.2 Cohen's d Effect Size
```
d = (mean_before - mean_after) / pooled_std
```
- Interpret: |d| < 0.2 (negligible), 0.2-0.5 (small), 0.5-0.8 (medium), > 0.8 (large)

### 4.3 Quality Metrics
- SNR improvement per modality
- Kurtosis change (indicates artifact removal)
- Variance reduction (noise removal)

---

## 5. Output Structure

```
output/
├── metrics/
│   ├── cleaning_validation.json      # Global validation results
│   └── s{000-015}_cleaning.json      # Per-subject metrics
├── figures/
│   ├── cleaning_comparison_{modality}_{subject}.png
│   ├── cleaning_spectrum_{modality}_{subject}.png
│   └── cleaning_dist_{modality}_{subject}.png
└── data/
    └── cleaned_signals.h5            # Cleaned signal cache (MNE format)
```

---

## 6. Key Functions to Implement

### src/biosignal/stages/cleaning.py

```python
# Filter functions
def apply_notch_filter(raw, freq=50, Q=30)
def apply_bandpass_filter(raw, low_freq, high_freq, order=4)
def apply_modality_filters(raw, modality)

# Interpolation
def detect_gaps(data, threshold=1e-6)
def interpolate_gaps(data, gaps, max_gap_s=1.0, sfreq=250)

# Outlier handling
def winsorize(data, limits=(0.05, 0.95))
def zscore_rejection(data, threshold=3.0)
def mad_rejection(data, threshold=3.5)

# Validation
def compute_effect_size(before, after)
def validate_cleaning(before_stats, after_stats)

# Visualization
def plot_before_after(raw_before, raw_after, modality, subject_id)
def plot_spectrum_comparison(raw_before, raw_after, modality, subject_id)

# Main
def run(subject_id=None, verbose=False)
```

---

## 7. Configuration Constants

```python
# src/biosignal/config.py additions

FILTER_CONFIG = {
    "eeg": {"low_freq": 0.5, "high_freq": 50, "notch_freq": 50},
    "ecg": {"low_freq": 0.5, "high_freq": 50, "notch_freq": 50},
    "emg": {"low_freq": 20, "high_freq": 250, "notch_freq": 50},
    "fnirs": {"low_freq": 0.01, "high_freq": 0.1, "notch_freq": None},
}

WINSORIZE_LIMITS = (0.05, 0.95)  # 5th and 95th percentile
ZSCORE_THRESHOLD = 3.0
MAD_THRESHOLD = 3.5
MAX_INTERPOLATION_GAP_S = 1.0
```

---

## 8. Dependencies

From `pyproject.toml`:
- scipy (butterworth filter design, signal processing)
- numpy (array operations)
- matplotlib (visualization)
- mne (filter implementation via `raw.filter()`)

---

## 9. Execution

```bash
# Run for all subjects
uv run python -m biosignal run 4 --verbose

# Run for specific subject
uv run python -m biosignal run 4 --subject 5 --verbose
```

---

## 10. Integration Points

- **Input:** Raw signals from Stage 1 acquisition (via `io/ieee.py`)
- **SQI Integration:** Reject segments flagged in Stage 2
- **Statistics Integration:** Use same statistical functions from Stage 3 for comparison
- **Output:** Cleaned signals for Stage 5 (Segmentation)

---

## 11. Expected Outcomes

- Powerline noise (50/60 Hz) removed from all modalities
- Band-specific frequency content preserved
- Extreme outliers handled via Winsorization
- SNR improvement > 3 dB expected
- Cohen's d effect size: medium to large for Kurtosis reduction