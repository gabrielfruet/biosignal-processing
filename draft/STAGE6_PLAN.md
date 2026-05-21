# Stage 6: Feature Extraction — Implementation Plan

## 1. Requirements Summary

From PRD.md Stage 6 requirements:

| Req ID | Requirement |
|--------|-------------|
| FE-001 | Extract time-domain features (RMS, MAV, Variance, ZCR, Hjorth) |
| FE-002 | Extract frequency-domain features (FFT, spectral power, band power) |
| FE-003 | Extract time-frequency features (Wavelet, STFT) |
| FE-004 | Extract nonlinear features (Entropy, Poincaré — ECG) |
| FE-005 | Organize features by domain category |

**Deliverable 6:**
- `data/s{id}_{modality}_features.csv` — per-subject feature matrices
- Feature distribution plots and correlation heatmaps
- `metrics/features_metrics.json` — global summary

---

## 2. Modality Scope

fNIRS is **definitively excluded** (2.5% window retention from Stage 5). Active modalities:

| Modality | Channels | Fs (Hz) | Feature Focus |
|----------|----------|---------|---------------|
| EEG | 8 | 512 | Time + band-power + Hjorth |
| ECG | 1 | 250 | Time + HRV (time & freq domain) |
| EMG | 1 | 250 | Time + frequency (RMS, MNF, MDF) |

---

## 3. Feature Set

### 3.1 Time-Domain Features (all modalities, per channel)

| Feature | Formula | ID |
|---------|---------|-----|
| RMS | `sqrt(mean(x²))` | rms |
| MAV | `mean(abs(x))` | mav |
| Variance | `var(x)` | variance |
| ZCR | sign-change count / N | zcr |
| Hjorth Activity | `var(x)` | hjorth_activity |
| Hjorth Mobility | `sqrt(var(dx) / var(x))` | hjorth_mobility |
| Hjorth Complexity | `mobility(dx) / mobility(x)` | hjorth_complexity |
| Skewness | `scipy.stats.skew(x)` | skewness |
| Kurtosis | `scipy.stats.kurtosis(x)` | kurtosis |

### 3.2 Frequency-Domain Features (Welch PSD, per channel)

| Feature | Description | Modalities |
|---------|-------------|-----------|
| `total_power` | Integral of PSD | all |
| `mean_freq` | Power-weighted mean frequency | all |
| `median_freq` | Frequency at 50% cumulative power | all |
| `spectral_entropy` | Normalized spectral entropy | all |
| `delta_power` | 0.5–4 Hz band power | EEG |
| `theta_power` | 4–8 Hz band power | EEG |
| `alpha_power` | 8–13 Hz band power | EEG |
| `beta_power` | 13–30 Hz band power | EEG |
| `gamma_power` | 30–50 Hz band power | EEG |

### 3.3 ECG-Specific HRV Features

R-peak detection via `scipy.signal.find_peaks` on the raw window signal.

**Time domain HRV:**
| Feature | Description |
|---------|-------------|
| `mean_rr` | Mean RR interval (ms) |
| `sdnn` | Std of RR intervals |
| `rmssd` | RMS of successive RR differences |
| `pnn50` | % of successive RR diffs > 50 ms |

**Frequency domain HRV** (from interpolated RR tachogram):
| Feature | Band |
|---------|------|
| `lf_power` | 0.04–0.15 Hz |
| `hf_power` | 0.15–0.40 Hz |
| `lf_hf_ratio` | LF / HF |

---

## 4. Implementation Strategy

### 4.1 Data Flow

```
Stage 5 NPZ → load windows (n_windows × n_channels × n_samples)
            → per window × per channel: extract_features_window()
            → DataFrame → CSV + JSON
```

### 4.2 Core Functions

```python
def _hjorth(x) -> tuple[float, float, float]
def _zcr(x) -> float
def _band_power(freqs, psd, fmin, fmax) -> float

def compute_time_domain(x) -> dict
def compute_frequency_domain(x, fs, modality) -> dict
def compute_hrv_features(x, fs) -> dict          # ECG only

def extract_features_window(x, fs, modality) -> dict
def run(subject_id=None, verbose=False) -> None
```

### 4.3 Loading Stage 5 Segments

```python
data = np.load(STAGE5_DATA_DIR / f"s{id:03d}_{modality}_segments.npz", allow_pickle=True)
windows = data['windows']    # (n_windows, n_channels, n_samples)
metadata = json.loads(str(data['metadata']))
```

---

## 5. Output Structure

```
output/stage6_features/
├── data/
│   ├── s000_eeg_features.csv
│   ├── s000_ecg_features.csv
│   ├── s000_emg_features.csv
│   └── ... (3 modalities × 16 subjects = 48 CSVs)
├── metrics/
│   ├── s000_features.json
│   └── features_metrics.json
└── figures/
    ├── feature_distributions_eeg.png
    ├── feature_distributions_ecg.png
    ├── feature_distributions_emg.png
    ├── feature_correlation_eeg.png
    ├── feature_correlation_ecg.png
    ├── feature_correlation_emg.png
    └── eeg_band_power_summary.png
```

### CSV Column Schema

```
subject_id, modality, window_id, channel, start_s, end_s,
rms, mav, variance, zcr,
hjorth_activity, hjorth_mobility, hjorth_complexity,
skewness, kurtosis,
mean_freq, median_freq, total_power, spectral_entropy,
[delta_power, theta_power, alpha_power, beta_power, gamma_power]  # EEG only
[mean_rr, sdnn, rmssd, pnn50, lf_power, hf_power, lf_hf_ratio]   # ECG only
```

---

## 6. Visualizations

1. **Feature distribution boxplots** — all features aggregated across subjects
   - `feature_distributions_{modality}.png`
2. **Feature correlation heatmap** — Pearson r between all features
   - `feature_correlation_{modality}.png`
3. **EEG band-power bar chart** — mean band powers per subject
   - `eeg_band_power_summary.png`

---

## 7. Configuration Constants (config.py)

```python
STAGE6_DIR = OUTPUT_DIR / "stage6_features"
STAGE6_METRICS_DIR = STAGE6_DIR / "metrics"
STAGE6_FIGURES_DIR = STAGE6_DIR / "figures"
STAGE6_DATA_DIR = STAGE6_DIR / "data"
```

---

## 8. Dependencies

All already available in `pyproject.toml`:
- `numpy` — array operations
- `scipy` — Welch PSD, `find_peaks`, `skew`, `kurtosis`
- `pandas` — DataFrame / CSV output
- `matplotlib` — visualization

---

## 9. Execution

```bash
# Run for single subject (validation)
uv run python -m biosignal run 6 --subject 0 --verbose

# Run for all subjects
uv run python -m biosignal run 6 --verbose
```

---

## 10. Integration Points

- **Input:** Stage 5 NPZ segments from `output/stage5_segmentation/data/segments/`
- **Output:** Feature CSVs and metrics for Stage 7 (Feature Engineering)

---

## 11. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | CSV created per subject per modality | `ls output/stage6_features/data/` |
| 2 | All time-domain features present in CSV | Check column names |
| 3 | EEG band powers (delta–gamma) in EEG CSV | Check column names |
| 4 | ECG HRV features present in ECG CSV | Check column names |
| 5 | Per-subject JSON metrics saved | `ls output/stage6_features/metrics/` |
| 6 | Global summary JSON saved | `features_metrics.json` exists |
| 7 | 3 plot types per modality generated | `ls output/stage6_features/figures/` |
| 8 | CLI command works | `uv run python -m biosignal run 6` |
| 9 | fNIRS skipped (not processed) | No `fnirs` CSV in output |
