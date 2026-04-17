# New Session Guide

## Project: Biosignal Processing Pipeline (BioSignal-Process)

**Goal:** Transform raw biosignal data (ECG, EMG, EEG, PPG, GSR, Respiratory) from IEEE Multimodal Emotion Recognition dataset into validated, feature-rich dataset for machine learning.

---

## Quick Start Commands

```bash
# Navigate to project
cd /home/pauloricms/Documents/Materias_UFC/Biossinais/biosignal-processing

# Run any pipeline stage
uv run python -m biosignal run <1-10>

# Run with verbose output
uv run python -m biosignal run 4 --verbose

# Run for specific subject
uv run python -m biosignal run 4 --subject 5 --verbose

# List available stages
uv run python -m biosignal list-stages
```

---

## Completed Pipeline Stages

| Stage | Status | Command | Output |
|-------|--------|---------|--------|
| 1. Acquisition | ✅ | `run 1` | `metrics/s*_acquisition.json`, `*_raw_signals.png` |
| 2. SQI | ✅ | `run 2` | `metrics/sqi_metrics.json`, `sqi_heatmap.png` |
| 3. Statistics | ✅ | `run 3` | `metrics/statistics.json`, histograms/boxplots |
| 4. Cleaning | ✅ | `run 4` | `metrics/cleaning_validation.json`, comparison plots |

---

## Current State (April 16, 2026)

### Stage 4 Just Completed
- **Notch filter** (50 Hz) for powerline removal
- **Band-pass filter** (modality-specific: EEG 0.5-50Hz, ECG 0.5-50Hz, EMG 20-250Hz, fNIRS 0.01-0.1Hz)
- **Gap interpolation** (linear, gaps < 1s)
- **Winsorization** (5th-95th percentile)
- **Z-score rejection** (threshold=3.0)

**Bug Fixed during Stage 4:** `interpolate_gaps()` had index boundary issue - corrected linear interpolation logic.

---

## Next Steps (Stage 5-10)

### Stage 5: Segmentation (Windowing)
- Fixed window segmentation (1s, 5s options)
- Overlapping windows support
- Event-based physiological segmentation

### Stage 6: Feature Extraction
- Time-domain: RMS, MAV, Variance, ZCR, Hjorth
- Frequency-domain: FFT, spectral power, band power
- Time-frequency: Wavelet, STFT
- Nonlinear: Entropy, DFA, Fractal dimension, Poincaré

### Stages 7-10
- Feature Engineering → Dimensionality Reduction → Feature Selection → Final Validation

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/PRD.md` | Full project requirements |
| `docs/ARCHITECTURE.md` | Project structure, CLI commands |
| `docs/CONTEXT.md` | Current project status |
| `src/biosignal/stages/cleaning.py` | Stage 4 implementation |
| `src/biosignal/config.py` | Configuration constants |
| `output/metrics/cleaning_validation.json` | Stage 4 output |

---

## Dataset Info

- **16 subjects** (s000-s015)
- **Modalities:** EEG (8ch @ 512Hz), ECG (1ch @ 250Hz), EMG (1ch @ 250Hz), fNIRS (2ch @ 16Hz)
- **Task:** Emotion induction (baseline 30s → stimulation 30s → recovery)

---

## Important Notes

1. **Python package:** Uses `uv` for dependency management
2. **Data location:** `data/ieee-multimodal-extracted/{subject_id}/`
3. **Output location:** `output/{metrics,figures,data}/`
4. **Next stage to implement:** `src/biosignal/stages/segmentation.py`
5. **CLI registration:** Update `src/biosignal/cli.py` `_get_stage_func()` for new stages