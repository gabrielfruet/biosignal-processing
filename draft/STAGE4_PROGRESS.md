# Stage 4: Data Cleaning & Correction - Progress Report

## Execution Date
April 16, 2026

## Status: ✅ Complete

All 16 subjects successfully processed through Stage 4 cleaning pipeline.

---

## Pipeline Applied

For each modality, the following cleaning steps were applied in sequence:

1. **Notch Filter** (50 Hz) - Powerline noise removal
2. **Band-Pass Filter** - Modality-specific frequency range
3. **Gap Interpolation** - Linear interpolation for flat-line gaps < 1s
4. **Winsorization** (5th-95th percentile) - Extreme outlier handling
5. **Z-score Rejection** (threshold=3.0) - MAD-based clipping

---

## Modality-Specific Filter Specifications

| Modality | Band-Pass (Hz) | Notch (Hz) | Order |
|----------|----------------|------------|-------|
| EEG | 0.5 - 50 | 50 | 4 |
| ECG | 0.5 - 50 | 50 | 4 |
| EMG | 20 - 250 | 50 | 4 |
| fNIRS | 0.01 - 0.1 | N/A | 2 |

---

## Output Files Generated

### Metrics
- `output/metrics/cleaning_validation.json` - Global validation + per-subject metrics
- `output/metrics/s000_cleaning.json` through `s015_cleaning.json` - Per-subject detailed metrics

### Figures
- `cleaning_comparison_{subject}_{modality}.png` - Before/after signal overlay (16 subjects × 4 modalities = 64 files)
- `cleaning_spectrum_{subject}_{modality}.png` - Spectral density comparison
- `cleaning_dist_{subject}_{modality}.png` - Distribution histogram comparison

---

## Key Metrics Tracked

Per channel:
- Variance before/after + reduction percentage
- Kurtosis before/after
- SNR before/after + improvement (dB)
- Cohen's d effect size
- Samples interpolated
- Samples winsorized

Global summary:
- Total samples interpolated across all subjects
- Total samples winsorized
- Mean SNR improvement

---

## Notes

### Bug Fixed: Interpolation Gap Detection
- Initial implementation had index boundary issue in `interpolate_gaps()`
- Fixed by properly indexing known points (start-1, end) for linear interpolation
- Error was: `fp and xp are not of the same length`

### fNIRS Processing
- fNIRS signals have very low amplitude (range: -0.000001 to 0.000001)
- Band-pass filter (0.01-0.1 Hz) applied to preserve hemodynamic oscillations
- Very few samples detected as gaps due to low-frequency nature

### Filter Robustness
- Added safe fallbacks for band-pass filter design
- Returns original data if filter design fails (invalid frequency ratios)

---

## Integration with Previous Stages

| Stage | Output Used |
|-------|-------------|
| Stage 1 | Raw signal data via `io/ieee.load()` |
| Stage 2 | SQI rejection information (not yet integrated) |
| Stage 3 | Statistical baseline for comparison |

### Next Integration Step
Stage 4 should incorporate SQI segment rejection info from Stage 2 to skip/remove low-quality segments before cleaning.

---

## Open Items for Future Stages

1. **Stage 5 (Segmentation):** Use cleaned signals from Stage 4 output
2. **Cached Cleaning:** Consider saving cleaned signals to avoid re-processing
3. **SQI Integration:** Reject segments flagged in Stage 2 before feature extraction