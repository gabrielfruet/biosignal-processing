# Implementation Plan: Stage 3 - Initial Statistical Analysis

## Overview

Stage 3 performs comprehensive statistical analysis on the biosignal data, computing descriptive statistics, normality/homoscedasticity tests, and generating visualizations to understand data distribution before further processing.

## Requirements from PRD (STA-001 to STA-007)

| Req ID | Requirement |
|--------|-------------|
| STA-001 | Compute descriptive statistics (mean, median, variance, SD) |
| STA-002 | Calculate quartiles and IQR |
| STA-003 | Generate histograms and boxplots |
| STA-004 | Apply normality tests (Shapiro-Wilk, Kolmogorov-Smirnov) |
| STA-005 | Apply homoscedasticity tests (Levene, Bartlett) |
| STA-006 | Generate Q-Q plots |
| STA-007 | Compute correlation matrix with heatmap |

## Deliverables

1. **`output/metrics/statistics.json`** - All test results in JSON format
2. **`output/figures/stat_histogram_{subject}_{modality}.png`** - Histograms per subject/modality
3. **`output/figures/stat_boxplot_{subject}_{modality}.png`** - Boxplots per subject/modality
4. **`output/figures/stat_qq_{subject}_{modality}.png`** - Q-Q plots per subject/modality
5. **`output/figures/stat_correlation_heatmap.png`** - Correlation heatmap across all subjects

## File Changes

### 1. Create `src/biosignal/stages/statistics.py`

**New file** implementing Stage 3 with the following functions:

```
Functions:
├── compute_descriptive_stats(data) -> dict
│   └── Returns: mean, median, variance, std, min, max, range, skewness, kurtosis
├── compute_quartiles(data) -> dict  
│   └── Returns: q1, q2 (median), q3, iqr, percentiles (10, 25, 50, 75, 90)
├── test_normality(data) -> dict
│   └── Returns: shapiro_wilk (stat, p-value), ks_test (stat, p-value), is_normal (bool)
├── test_homoscedasticity(data_groups) -> dict
│   └── Returns: levene (stat, p-value), bartlett (stat, p-value), is_homoscedastic (bool)
├── plot_histogram(data, modality, channel, subject_id) -> None
│   └── Saves histogram with normal curve overlay
├── plot_boxplot(data, modality, subject_id) -> None
│   └── Saves boxplot showing distribution across channels
├── plot_qq(data, modality, channel, subject_id) -> None
│   └── Saves Q-Q plot for normality assessment
├── plot_correlation_heatmap(all_data, subject_id) -> None
│   └── Saves correlation heatmap across modalities/channels
└── run(subject_id, verbose) -> None
    └── Main entry point
```

**Key implementation details:**

- Process EEG (8 channels), ECG, EMG, and fNIRS (2 channels) separately
- For EEG, analyze per-channel and aggregate statistics
- Use 5-second windows (consistent with SQI) for segment-level analysis
- For normality tests, use a sample of max 5000 points (scipy limitation)
- For correlation matrix: compute inter-modality and inter-channel correlations
- Include interpretation text in JSON output (e.g., "Data appears normally distributed based on Shapiro-Wilk p > 0.05")

### 2. Update `src/biosignal/stages/__init__.py`

Add `statistics` to the imports and `__all__` list:

```python
from biosignal.stages import acquisition, sqi, statistics

__all__ = [
    "acquisition",
    "sqi", 
    "statistics",
]
```

### 3. Update `src/biosignal/cli.py`

Add lazy loading for Stage 3 in `_get_stage_func()`:

```python
elif stage == 3:
    from biosignal.stages import statistics
    _STAGE_FUNCTIONS[stage] = statistics.run
```

## Output Structure

**`output/metrics/statistics.json`**:
```json
{
  "subjects_analyzed": 16,
  "per_subject": {
    "000": {
      "eeg": {
        "descriptive": { "channels": {...}, "aggregate": {...} },
        "quartiles": { "channels": {...}, "aggregate": {...} },
        "normality": { "channels": {...}, "aggregate": {...} },
        "homoscedasticity": { "between_channels": {...} }
      },
      "ecg": { ... },
      "emg": { ... },
      "fnirs": { ... }
    },
    ...
  },
  "correlation_matrix": { "subjects_aggregate": {...} },
  "interpretation": {
    "normality_summary": "...",
    "homoscedasticity_summary": "...",
    "correlation_summary": "..."
  }
}
```

## Visualization Specifications

| Plot | Description | Style |
|------|-------------|-------|
| Histogram | Distribution with normal curve overlay | 8 subplots (EEG), 1 per modality for others |
| Boxplot | Shows median, quartiles, outliers | Grouped by modality |
| Q-Q Plot | Normality visualization | Reference diagonal line |
| Heatmap | Correlation matrix | Diverging colormap (blue-white-red) |

## Testing Considerations

1. **Missing data**: Handle NaN values gracefully (skip in calculations, document in output)
2. **Small samples**: For Shapiro-Wilk with n < 3, note as "insufficient data"
3. **Large samples**: K-S test can be overly sensitive; use combined interpretation
4. **Modality differences**: EEG has 8 channels, ECG/EMG have 1, fNIRS has 2

## Dependencies (already in project)

- `numpy` - Statistical calculations
- `scipy.stats` - Normality tests, kurtosis, skewness
- `matplotlib` - Visualizations

No new dependencies needed.

## Validation Steps

After implementation, verify:
1. `uv run python -m biosignal run 3 --verbose` completes without errors
2. `output/metrics/statistics.json` contains all required statistics
3. All figure files are generated in `output/figures/`
4. Output matches the structure specified in the PRD deliverables
