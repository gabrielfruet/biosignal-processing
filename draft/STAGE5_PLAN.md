# Stage 5: Segmentation (Windowing) - Implementation Plan

## 1. Requirements Summary

From PRD.md Stage 5 requirements:

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

## 2. Modality-Specific Window Specifications

### Based on Dataset Characteristics

| Modality | Sampling Rate | Fixed Window (1s) | Fixed Window (5s) | Overlap Options |
|----------|--------------|------------------|------------------|-----------------|
| EEG | 512 Hz | 512 samples | 2560 samples | 0.25s, 0.5s, 2.5s |
| ECG | 250 Hz | 250 samples | 1250 samples | 0.25s, 0.5s |
| EMG | 250 Hz | 250 samples | 1250 samples | 0.25s, 0.5s |
| fNIRS | 16 Hz | 16 samples | 80 samples | 2s, 4s |

### Window Size Selection Rationale
- **1 second windows:** Suitable for transient analysis (ERP, EMG bursts)
- **5 second windows:** Aligned with SQI stage (consistency), captures enough cycles for frequency-domain analysis
- **Overlap:** Allows smoother transitions and better temporal resolution

---

## 3. Implementation Strategy

### 3.1 Fixed Window Segmentation

```python
def create_fixed_windows(data, sfreq, window_size_s, overlap_s=0):
    """
    Create non-overlapping or overlapping fixed-size windows.
    
    Args:
        data: Signal data (n_channels, n_samples)
        sfreq: Sampling frequency
        window_size_s: Window duration in seconds
        overlap_s: Overlap duration in seconds (0 = no overlap)
    
    Returns:
        windows: Array of shape (n_windows, n_channels, window_samples)
        metadata: Window timing information
    """
```

### 3.2 Event-Based Segmentation

Use marker information from dataset:
- `baseline_start` → baseline window
- `stim_start` → stimulation window
- `stim_end` → recovery window

```python
def segment_by_events(data, markers, sfreq, window_before_s=5, window_after_s=30):
    """
    Segment based on experimental markers.
    
    Args:
        data: Signal data
        markers: Dict with 'baseline', 'stim_start', 'stim_end'
        sfreq: Sampling frequency
        window_before_s: Seconds before event
        window_after_s: Seconds after event
    
    Returns:
        segments: Dict of labeled segments
    """
```

### 3.3 Integration with SQI Rejection

Segments flagged by SQI (Stage 2) should be excluded:
- Load SQI metrics from `output/metrics/s{subject_id}_sqi.json`
- Mark rejected windows as invalid
- Track rejection rate per subject/modality

---

## 4. Validation Metrics

### 4.1 Intra-Window Stability
- **Coefficient of Variation (CV):** CV < 30% indicates stable window
- **Variance within window:** Track per-channel variance
- **Stationarity test:** Augmented Dickey-Fuller (ADF) per window

### 4.2 Inter-Window Variance
- **Between-window variance:** Measures consistency across trials
- **CV across windows:** Should be lower than CV within windows for good data
- **Plot:** Variance heatmap across windows

### 4.3 Quality Metrics
- Total windows created
- Windows rejected by SQI
- Net usable windows
- Rejection rate per modality

---

## 5. Output Structure

```
output/
├── metrics/
│   ├── segmentation_metrics.json      # Global segmentation metrics
│   └── s{000-015}_segmentation.json    # Per-subject segmentation details
├── figures/
│   ├── segmentation_windows_{subject}_{modality}.png
│   ├── window_stability_{subject}_{modality}.png
│   └── inter_window_variance_{subject}_{modality}.png
└── data/
    └── segments/
        └── s{subject_id}_{modality}_segments.npz  # Windowed data cache
```

---

## 6. Key Functions to Implement

### src/biosignal/stages/segmentation.py

```python
# Window creation
def create_fixed_windows(data, sfreq, window_size_s, overlap_s=0.0)
def create_overlapping_windows(data, sfreq, window_size_s, overlap_ratio=0.5)

# Event-based segmentation
def segment_by_markers(data, markers, sfreq, window_before_s, window_after_s)

# SQI integration
def load_sqi_rejected_segments(subject_id, modality)
def filter_windows_by_quality(windows, rejected_indices)

# Validation metrics
def compute_intra_window_stability(windows)
def compute_inter_window_variance(windows)
def adf_stationarity_test(signal_segment)

# Visualization
def plot_windowed_signal(data, window_starts, sfreq, modality, subject_id)
def plot_window_stability(stability_metrics, modality, subject_id)
def plot_inter_window_variance(variance_metrics, modality, subject_id)

# Main
def run(subject_id=None, verbose=False)
```

---

## 7. Configuration Constants

```python
# src/biosignal/config.py additions

SEGMENTATION_CONFIG = {
    "window_sizes": {
        "eeg": {"fixed_1s": 512, "fixed_5s": 2560},
        "ecg": {"fixed_1s": 250, "fixed_5s": 1250},
        "emg": {"fixed_1s": 250, "fixed_5s": 1250},
        "fnirs": {"fixed_1s": 16, "fixed_5s": 80},
    },
    "overlap_options": [0.0, 0.25, 0.5, 0.75],
    "default_window": "5s",
    "stability_threshold_cv": 0.30,  # CV < 30% = stable
}

# Event-based segmentation
EVENT_WINDOW_CONFIG = {
    "baseline": {"before": 0, "after": 30},  # 30s baseline
    "stimulation": {"before": 0, "after": 30},  # 30s stimulation
    "recovery": {"before": 0, "after": 30},  # 30s recovery
}
```

---

## 8. Dependencies

From `pyproject.toml` (already available):
- numpy (array operations)
- scipy (ADF stationarity test)
- matplotlib (visualization)
- mne (signal handling)

New imports:
```python
from statsmodels.tsa.stattools import adfuller  # stationarity test
```

---

## 9. Execution

```bash
# Run for all subjects
uv run python -m biosignal run 5 --verbose

# Run for specific subject
uv run python -m biosignal run 5 --subject 5 --verbose

# Run with 1s windows
uv run python -m biosignal run 5 --window-size 1 --verbose

# Run with overlapping windows (50% overlap)
uv run python -m biosignal run 5 --window-size 5 --overlap 0.5 --verbose
```

---

## 10. Integration Points

- **Input:** Cleaned signals from Stage 4 (via `io/ieee.py`)
- **SQI Integration:** Load rejected segments from `Stage 2` (`sqi_metrics.json`)
- **Markers Integration:** Use experimental markers for event-based segmentation
- **Output:** Segmented windows for Stage 6 (Feature Extraction)

---

## 11. Expected Outcomes

- All modalities segmented into fixed windows (5s default)
- SQI rejection information propagated to segmentation
- Rejection rate documented per subject/modality:
  - EEG: ~6% expected (from SQI Stage 2)
  - ECG: ~35% expected
  - EMG: ~56% expected
  - fNIRS: ~97% expected (excluded from ML stages)
- Intra-window stability validated (CV < 30% for good segments)
- Inter-window variance computed and visualized

---

## 12. Files to Create

1. `src/biosignal/stages/segmentation.py` - Main implementation
2. Update `src/biosignal/stages/__init__.py` - Add segmentation import
3. Update `src/biosignal/cli.py` - Add Stage 5 CLI handler

---

## 13. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Non-overlapping 5s windows created | Check output/data/segments/ |
| 2 | Overlapping windows supported (configurable overlap) | CLI with --overlap flag |
| 3 | Event-based segmentation works | Markers used correctly |
| 4 | SQI rejection propagated | Rejected windows marked |
| 5 | Intra-window stability computed | CV values in metrics |
| 6 | Inter-window variance analyzed | Variance plots generated |
| 7 | Per-subject segmentation JSON saved | `s*_segmentation.json` exists |
| 8 | Global segmentation JSON saved | `segmentation_metrics.json` exists |
| 9 | CLI command works | `uv run python -m biosignal run 5` |
| 10 | Ruff/basedpyright passes | Linting checks pass |