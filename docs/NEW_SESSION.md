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

### Stage 5 Completed - Segmentation Results

**Global Metrics (All 16 Subjects):**

| Modality | Total Windows | Usable | Retention | CV Mean | ADF Stationary |
|----------|--------------|--------|-----------|---------|----------------|
| EEG (8ch) | 329 | 309 | 93.9% | 1.82% | 0.0% |
| ECG | 334 | 216 | 64.7% | 11.37% | 97.7% |
| EMG | 334 | 147 | 44.0% | 1.59% | 14.3% |
| fNIRS | 314 | 8 | 2.5% | 3495% | 100% |

**Key Findings:**
- **EEG:** Excellent uniformity (CV < 2%), 0% ADF stationary (expected for dynamic cortical potentials)
- **ECG:** 97.7% ADF stationary (quasi-periodic heartbeat), higher CV variability
- **EMG:** 56% rejection due to movement artifacts during emotional induction
- **fNIRS:** Confirmed exclusion from pipeline (>97% rejection)

**Problematic Subjects:**
- ECG < 30% retention: s003, s004, s006, s013
- EMG 0% usable: s002, s015

**Correlations:**
- EEG-ECG: r=0.24 (weak)
- ECG-EMG: r=-0.25 (weak, negative)
- Artifacts are modality-specific, not correlated with general participant state

---

## Segmentation Stage Features

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

## Next Steps (Stage 6-10)

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
| `docs/NEW_SESSION.md` | This file - quick reference |
| `src/biosignal/stages/segmentation.py` | Stage 5 implementation |
| `src/biosignal/config.py` | Configuration constants |
| `tex/documento.tex` | Academic document (updated with Stage 5) |
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

## Document Section for Stage 5

**Location:** `tex/2-textuais/3-metodologia.tex` and `tex/2-textuais/4-resultados.tex`

**New Sections Added:**
- `3-metodologia.tex`: Section "Segmentação Temporal (Janelamento)" (Sec. 6)
- `4-resultados.tex`: Section "Segmentação Temporal dos Sinais" with:
  - Table: `tab:segmentacao_summary` - Global retention by modality
  - Table: `tab:segmentacao_metrics` - Stability metrics (CV, ADF) for s000
  - Table: `tab:subjects_segmentacao` - Per-subject detailed analysis
  - Figures: `window_stability_000_eeg.png`, `inter_window_variance_000_eeg.png`, `segmentation_windows_000_eeg.png`
  - 6 key observations documented

---

## Important Notes

1. **Python package:** Uses `uv` for dependency management
2. **Data location:** `data/ieee-multimodal-extracted/{subject_id}/`
3. **Output location:** `output/{metrics,figures,data}/`
4. **CLI options:** Use `--window-size` and `--overlap` for Stage 5
5. **Next stage to implement:** `src/biosignal/stages/features.py` (Stage 6)
6. **CLI registration:** Update `src/biosignal/cli.py` `_get_stage_func()` for new stages
7. **When updating documents:** Always analyze JSON metrics before writing to .tex

---

## pi Skill: biosignal-tex

A project-specific pi skill is available at `.pi/skills/biosignal-tex/`

**Purpose:** Guide document updates with real metrics after pipeline stages

**Usage:**
```bash
# Analyze metrics for a stage
python .pi/skills/biosignal-tex/analyze_metrics.py 5
```

**Contents:**
- `SKILL.md` - Instructions for .tex content generation
- `analyze_metrics.py` - Quick metrics summary script

**Workflow:**
1. Run pipeline stage → generates JSON metrics
2. Run analyzer script → shows report-ready summary
3. Update .tex with real values + appropriate figures
4. Compile: `cd tex && make`
5. Update this file (NEW_SESSION.md)
