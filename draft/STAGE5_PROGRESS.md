# Stage 5: Segmentation (Windowing) - Progress Report

## Execution Date
May 6, 2026

## Status: ✅ Complete

All 16 subjects successfully processed through Stage 5 segmentation pipeline.

---

## Implementation Summary

### Files Created/Modified

| File | Action |
|------|--------|
| `pyproject.toml` | Added `statsmodels>=0.14` dependency |
| `src/biosignal/config.py` | Added `SEGMENTATION_CONFIG`, `SEGMENT_DATA_DIR` |
| `src/biosignal/stages/segmentation.py` | **Created** (~700 lines) |
| `src/biosignal/stages/__init__.py` | Added segmentation import |
| `src/biosignal/cli.py` | Added `--window-size` and `--overlap` options |

---

## Features Implemented

### 1. Fixed Window Segmentation
- Non-overlapping windows (default 5s)
- Overlapping windows (configurable overlap)
- Modality-specific window sizes:
  - EEG: 512 samples (1s), 2560 samples (5s)
  - ECG: 250 samples (1s), 1250 samples (5s)
  - EMG: 250 samples (1s), 1250 samples (5s)
  - fNIRS: 16 samples (1s), 80 samples (5s)

### 2. SQI Integration
- Loads rejection info from Stage 2 (`s{sID}_sqi.json`)
- Propagates rejection information to windows
- Tracks rejected windows in metrics

### 3. Stability Metrics
- **Intra-window stability (CV):** Coefficient of Variation per window
- **ADF Stationarity Test:** Augmented Dickey-Fuller test per window
- **Inter-window variance:** Between-window variance analysis
- Threshold: CV < 30% = stable window

### 4. Event-Based Segmentation
- `segment_by_markers()` function available
- Uses experimental markers (baseline, stim_start, stim_end)
- Note: Not yet integrated into main pipeline

---

## Output Files Generated

### Metrics
- `output/metrics/segmentation_metrics.json` - Global summary
- `output/metrics/s000_segmentation.json` through `s015_segmentation.json` - Per-subject details

### Cached Segments
- `output/data/segments/s{sID}_{mod}_segments.npz` - 64 files total
  - Contains: `windows` array, `metadata` JSON

### Figures (177 total)
- `segmentation_windows_{subj}_{mod}.png` - Window overlay visualization
- `window_stability_{subj}_{mod}.png` - CV/variance stability plots
- `inter_window_variance_{subj}_{mod}.png` - Inter-window variance summary

---

## Key Metrics (Subject 0)

| Modality | Total Windows | SQI Rejected | Usable | Stability Rate |
|----------|--------------|--------------|--------|----------------|
| EEG | 28 | 17.9% | 23 | 100.0% |
| ECG | 51 | 68.6% | 16 | 18.8% |
| EMG | 51 | 52.9% | 24 | 100.0% |
| fNIRS | 28 | 85.7% | 4 | 0.0% |

---

## CLI Usage

```bash
# Run full Stage 5 (default: 5s windows, no overlap)
uv run python -m biosignal run 5 --verbose

# Run for specific subject
uv run python -m biosignal run 5 --subject 5 --verbose

# Run with 1s windows
uv run python -m biosignal run 5 --window-size 1 --verbose

# Run with 50% overlap (2.5s overlap on 5s windows)
uv run python -m biosignal run 5 --overlap 2.5 --verbose
```

---

## Integration Points

| Stage | Connection |
|-------|------------|
| Stage 2 (SQI) | Loads rejection info from `s{sID}_sqi.json` |
| Stage 4 (Cleaning) | Uses cleaned signals via `io/ieee.load()` |
| Stage 6 (Features) | Can load cached segments from `output/data/segments/` |

---

## Open Items

1. **Event-based segmentation not integrated:** `segment_by_markers()` function exists but not called in main `run()` - could be added as optional mode
2. **No overlapping window metrics:** Inter-window variance computed but overlap-specific analysis not implemented
3. **fNIRS very low stability:** fNIRS shows 0% stability rate due to hemodynamic signal characteristics - may need modality-specific CV threshold

---

## Next Steps

1. **Stage 6 (Feature Extraction):** Use cached segments from `output/data/segments/` for feature computation
2. **Integrate event-based segmentation:** Add optional `--event-based` flag
3. **Consider fNIRS threshold:** Lower CV threshold for fNIRS (~50% instead of 30%)