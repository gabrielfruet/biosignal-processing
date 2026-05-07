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
| 5. Segmentation | ✅ | `run 5` | `metrics/segmentation_metrics.json`, `data/segments/*.npz` |

---

## Current State (May 6, 2026)

### Stage 5 Just Completed
- **Fixed window segmentation** (1s, 5s options via `--window-size`)
- **Overlapping windows** support (via `--overlap`)
- **SQI integration** - propagates rejection info from Stage 2
- **Intra-window stability** - CV < 30% threshold + ADF stationarity test
- **Inter-window variance** analysis
- **Cached segments** - saved as `.npz` files for downstream stages

**Files generated:**
- Metrics: `metrics/s{sID}_segmentation.json`, `metrics/segmentation_metrics.json`
- Segments: `data/segments/s{sID}_{mod}_segments.npz` (64 files)
- Figures: `segmentation_windows_*.png`, `window_stability_*.png`, `inter_window_variance_*.png`

---

## Next Steps (Stage 5-10)

### Stage 5: Segmentation (Windowing)
- ✅ Fixed window segmentation (1s, 5s options)
- ✅ Overlapping windows support
- ✅ SQI rejection propagation
- ✅ Intra-window stability metrics (CV + ADF)
- ✅ Cached segments for Stage 6

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
| `src/biosignal/stages/segmentation.py` | Stage 5 implementation |
| `src/biosignal/config.py` | Configuration constants |
| `output/stage1_acquisition/` | Stage 1 output |
| `output/stage2_sqi/` | Stage 2 output |
| `output/stage3_statistics/` | Stage 3 output |
| `output/stage4_cleaning/` | Stage 4 output |
| `output/stage5_segmentation/` | Stage 5 output |

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
4. **CLI options:** Use `--window-size` and `--overlap` for Stage 5
5. **Next stage to implement:** `src/biosignal/stages/features.py` (Stage 6)
5. **CLI registration:** Update `src/biosignal/cli.py` `_get_stage_func()` for new stages