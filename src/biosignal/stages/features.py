"""Stage 6: Feature Extraction.

Extracts time-domain, frequency-domain, and HRV features from segmented
windows produced by Stage 5. fNIRS is excluded (< 2.5% window retention).
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from scipy.signal import find_peaks, welch

from biosignal.config import (
    CHANNELS,
    SFREQ,
    STAGE5_DATA_DIR,
    STAGE6_DATA_DIR,
    STAGE6_FIGURES_DIR,
    STAGE6_METRICS_DIR,
)

ACTIVE_MODALITIES = ["eeg", "ecg", "emg"]

EEG_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 50.0),
}

HRV_BANDS = {
    "lf": (0.04, 0.15),
    "hf": (0.15, 0.40),
}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _hjorth(x: np.ndarray) -> tuple[float, float, float]:
    """Return (activity, mobility, complexity) Hjorth parameters."""
    activity = float(np.var(x))
    dx = np.diff(x)
    var_dx = float(np.var(dx))
    mobility = float(np.sqrt(var_dx / activity)) if activity > 0 else 0.0
    ddx = np.diff(dx)
    var_ddx = float(np.var(ddx))
    mob_dx = float(np.sqrt(var_ddx / var_dx)) if var_dx > 0 else 0.0
    complexity = float(mob_dx / mobility) if mobility > 0 else 0.0
    return activity, mobility, complexity


def _zcr(x: np.ndarray) -> float:
    """Zero crossing rate: fraction of samples where sign changes."""
    signs = np.sign(x)
    signs[signs == 0] = 1
    crossings = np.sum(np.diff(signs) != 0)
    return float(crossings / (len(x) - 1)) if len(x) > 1 else 0.0


def _band_power(freqs: np.ndarray, psd: np.ndarray, fmin: float, fmax: float) -> float:
    """Integrate PSD within [fmin, fmax] using the trapezoidal rule."""
    mask = (freqs >= fmin) & (freqs <= fmax)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(psd[mask], freqs[mask]))


# ---------------------------------------------------------------------------
# Per-window feature extraction
# ---------------------------------------------------------------------------

def compute_time_domain(x: np.ndarray) -> dict[str, float]:
    activity, mobility, complexity = _hjorth(x)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        skewness = float(stats.skew(x))
        kurt = float(stats.kurtosis(x))
    return {
        "rms": float(np.sqrt(np.mean(x**2))),
        "mav": float(np.mean(np.abs(x))),
        "variance": float(np.var(x)),
        "zcr": _zcr(x),
        "hjorth_activity": activity,
        "hjorth_mobility": mobility,
        "hjorth_complexity": complexity,
        "skewness": skewness,
        "kurtosis": kurt,
    }


def compute_frequency_domain(
    x: np.ndarray, fs: int, modality: str
) -> dict[str, float]:
    nperseg = min(256, len(x))
    freqs, psd = welch(x, fs=fs, nperseg=nperseg)

    total_power = float(np.trapezoid(psd, freqs))
    if total_power > 0:
        norm_psd = psd / total_power
        mean_freq = float(np.sum(freqs * norm_psd) / np.sum(norm_psd))
        cumpower = np.cumsum(psd)
        median_freq = float(
            freqs[np.searchsorted(cumpower, cumpower[-1] / 2)] if len(freqs) > 0 else 0.0
        )
        norm_psd_safe = norm_psd + 1e-12
        spectral_entropy = float(-np.sum(norm_psd_safe * np.log2(norm_psd_safe)))
    else:
        mean_freq = 0.0
        median_freq = 0.0
        spectral_entropy = 0.0

    feats: dict[str, float] = {
        "total_power": total_power,
        "mean_freq": mean_freq,
        "median_freq": median_freq,
        "spectral_entropy": spectral_entropy,
    }

    if modality == "eeg":
        for band_name, (flo, fhi) in EEG_BANDS.items():
            feats[f"{band_name}_power"] = _band_power(freqs, psd, flo, fhi)

    return feats


def compute_hrv_features(x: np.ndarray, fs: int) -> dict[str, float]:
    """ECG-specific HRV features from R-peak detection."""
    min_distance = int(0.4 * fs)  # min 400 ms between peaks (~150 bpm max)
    height_threshold = np.mean(x) + 0.5 * np.std(x)

    peaks, _ = find_peaks(x, distance=min_distance, height=height_threshold)

    if len(peaks) < 2:
        return {
            "mean_rr": np.nan,
            "sdnn": np.nan,
            "rmssd": np.nan,
            "pnn50": np.nan,
            "lf_power": np.nan,
            "hf_power": np.nan,
            "lf_hf_ratio": np.nan,
        }

    rr_samples = np.diff(peaks)
    rr_ms = rr_samples / fs * 1000.0

    mean_rr = float(np.mean(rr_ms))
    sdnn = float(np.std(rr_ms, ddof=1)) if len(rr_ms) > 1 else np.nan
    successive_diffs = np.diff(rr_ms)
    rmssd = float(np.sqrt(np.mean(successive_diffs**2))) if len(successive_diffs) > 0 else np.nan
    pnn50 = float(np.mean(np.abs(successive_diffs) > 50.0) * 100) if len(successive_diffs) > 0 else np.nan

    # HRV frequency domain via interpolated RR tachogram
    lf_power = np.nan
    hf_power = np.nan
    lf_hf_ratio = np.nan

    if len(rr_ms) >= 4:
        try:
            t_rr = peaks[1:] / fs
            t_uniform = np.arange(t_rr[0], t_rr[-1], 1.0 / 4.0)  # 4 Hz resample
            rr_interp = np.interp(t_uniform, t_rr, rr_ms)
            rr_interp -= np.mean(rr_interp)

            nperseg = min(len(rr_interp), 64)
            freqs_hrv, psd_hrv = welch(rr_interp, fs=4.0, nperseg=nperseg)

            lf_power = _band_power(freqs_hrv, psd_hrv, *HRV_BANDS["lf"])
            hf_power = _band_power(freqs_hrv, psd_hrv, *HRV_BANDS["hf"])
            lf_hf_ratio = float(lf_power / hf_power) if hf_power > 0 else np.nan
        except Exception:
            pass

    return {
        "mean_rr": mean_rr,
        "sdnn": sdnn,
        "rmssd": rmssd,
        "pnn50": pnn50,
        "lf_power": lf_power,
        "hf_power": hf_power,
        "lf_hf_ratio": lf_hf_ratio,
    }


def extract_features_window(x: np.ndarray, fs: int, modality: str) -> dict[str, float]:
    """Extract all features for one channel of one window."""
    feats: dict[str, float] = {}
    feats.update(compute_time_domain(x))
    feats.update(compute_frequency_domain(x, fs, modality))
    if modality == "ecg":
        feats.update(compute_hrv_features(x, fs))
    return feats


# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------

def _plot_feature_distributions(df: pd.DataFrame, modality: str, out_dir: Path) -> None:
    feature_cols = [
        c for c in df.columns
        if c not in {"subject_id", "modality", "window_id", "channel", "start_s", "end_s"}
    ]
    n = len(feature_cols)
    if n == 0:
        return

    ncols = 4
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 3.5, nrows * 3))
    axes_flat = axes.flatten() if n > 1 else [axes]

    for i, col in enumerate(feature_cols):
        ax = axes_flat[i]
        data = df[col].dropna()
        if len(data) == 0:
            ax.set_visible(False)
            continue
        ax.boxplot(data, vert=True, patch_artist=True,
                   boxprops=dict(facecolor="#4C72B0", alpha=0.7))
        ax.set_title(col, fontsize=8)
        ax.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
        ax.tick_params(axis="y", labelsize=7)

    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle(f"Feature Distributions — {modality.upper()}", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_dir / f"feature_distributions_{modality}.png", dpi=120)
    plt.close(fig)


def _plot_feature_correlation(df: pd.DataFrame, modality: str, out_dir: Path) -> None:
    feature_cols = [
        c for c in df.columns
        if c not in {"subject_id", "modality", "window_id", "channel", "start_s", "end_s"}
    ]
    if len(feature_cols) < 2:
        return

    corr = df[feature_cols].dropna().corr()
    n = len(feature_cols)
    fig, ax = plt.subplots(figsize=(max(6, n * 0.7), max(5, n * 0.6)))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(feature_cols, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(feature_cols, fontsize=7)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title(f"Feature Correlation — {modality.upper()}", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir / f"feature_correlation_{modality}.png", dpi=120)
    plt.close(fig)


def _plot_eeg_band_power(all_dfs: list[pd.DataFrame], out_dir: Path) -> None:
    band_cols = [f"{b}_power" for b in EEG_BANDS]
    rows = []
    for df in all_dfs:
        if not all(c in df.columns for c in band_cols):
            continue
        subj = df["subject_id"].iloc[0]
        means = df[band_cols].mean()
        row = {"subject": f"s{subj:03d}"}
        for col in band_cols:
            row[col] = means[col]
        rows.append(row)

    if not rows:
        return

    summary = pd.DataFrame(rows).set_index("subject")
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(summary))
    width = 0.15
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    for i, col in enumerate(band_cols):
        ax.bar(x + i * width, summary[col], width, label=col.replace("_power", ""), color=colors[i], alpha=0.8)
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(summary.index, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Mean Band Power (µV²/Hz)")
    ax.set_title("EEG Mean Band Power per Subject")
    ax.legend(title="Band", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "eeg_band_power_summary.png", dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(subject_id: int | None = None, verbose: bool = False) -> None:
    for d in [STAGE6_DATA_DIR, STAGE6_METRICS_DIR, STAGE6_FIGURES_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list(range(16))

    all_subject_metrics: dict[int, Any] = {}
    eeg_dfs: list[pd.DataFrame] = []

    for sid in subjects:
        if verbose:
            print(f"[Stage 6] Processing subject s{sid:03d}...")

        subject_metrics: dict[str, Any] = {"subject_id": sid, "modalities": {}}

        for modality in ACTIVE_MODALITIES:
            seg_path = STAGE5_DATA_DIR / f"s{sid:03d}_{modality}_segments.npz"
            if not seg_path.exists():
                if verbose:
                    print(f"  [{modality}] No segments file found, skipping.")
                continue

            npz = np.load(seg_path, allow_pickle=True)
            windows: np.ndarray = npz["windows"]  # (n_windows, n_channels, n_samples)
            metadata_raw = npz["metadata"]
            try:
                metadata: list[dict] = json.loads(str(metadata_raw))
            except Exception:
                metadata = []

            n_windows, n_channels, _ = windows.shape
            fs = SFREQ[modality]
            ch_names = CHANNELS[modality]

            if verbose:
                print(f"  [{modality}] {n_windows} windows × {n_channels} channels")

            rows: list[dict] = []
            for w_idx in range(n_windows):
                meta = metadata[w_idx] if w_idx < len(metadata) else {}
                start_s = meta.get("start_s", float(w_idx * 5))
                end_s = meta.get("end_s", start_s + 5.0)

                for ch_idx in range(n_channels):
                    ch_name = ch_names[ch_idx] if ch_idx < len(ch_names) else str(ch_idx)
                    x = windows[w_idx, ch_idx, :].astype(float)

                    # skip flat/constant windows
                    if np.std(x) < 1e-10:
                        continue

                    feats = extract_features_window(x, fs, modality)
                    row = {
                        "subject_id": sid,
                        "modality": modality,
                        "window_id": w_idx,
                        "channel": ch_name,
                        "start_s": start_s,
                        "end_s": end_s,
                        **feats,
                    }
                    rows.append(row)

            if not rows:
                if verbose:
                    print(f"  [{modality}] No valid rows extracted.")
                continue

            df = pd.DataFrame(rows)
            csv_path = STAGE6_DATA_DIR / f"s{sid:03d}_{modality}_features.csv"
            df.to_csv(csv_path, index=False)

            feature_cols = [
                c for c in df.columns
                if c not in {"subject_id", "modality", "window_id", "channel", "start_s", "end_s"}
            ]
            feat_stats: dict[str, dict] = {}
            for col in feature_cols:
                col_data = df[col].dropna()
                if len(col_data) == 0:
                    continue
                feat_stats[col] = {
                    "mean": float(col_data.mean()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "n_valid": int(col_data.count()),
                }

            subject_metrics["modalities"][modality] = {
                "n_windows": n_windows,
                "n_rows_extracted": len(rows),
                "n_features": len(feature_cols),
                "features": feat_stats,
            }

            if modality == "eeg":
                eeg_dfs.append(df)

            if verbose:
                print(f"  [{modality}] {len(rows)} rows → {csv_path.name}")

        per_subj_path = STAGE6_METRICS_DIR / f"s{sid:03d}_features.json"
        with open(per_subj_path, "w") as f:
            json.dump(subject_metrics, f, indent=2)

        all_subject_metrics[sid] = subject_metrics

    # -----------------------------------------------------------------------
    # Aggregate plots across all subjects
    # -----------------------------------------------------------------------
    if verbose:
        print("[Stage 6] Generating aggregate plots...")

    for modality in ACTIVE_MODALITIES:
        csv_files = sorted(STAGE6_DATA_DIR.glob(f"s*_{modality}_features.csv"))
        if not csv_files:
            continue
        try:
            combined = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
            _plot_feature_distributions(combined, modality, STAGE6_FIGURES_DIR)
            _plot_feature_correlation(combined, modality, STAGE6_FIGURES_DIR)
        except Exception as e:
            if verbose:
                print(f"  [plot] {modality} error: {e}")

    if eeg_dfs:
        try:
            _plot_eeg_band_power(eeg_dfs, STAGE6_FIGURES_DIR)
        except Exception as e:
            if verbose:
                print(f"  [plot] EEG band power error: {e}")

    # -----------------------------------------------------------------------
    # Global summary
    # -----------------------------------------------------------------------
    total_rows = 0
    modality_totals: dict[str, int] = {m: 0 for m in ACTIVE_MODALITIES}
    for sid_metrics in all_subject_metrics.values():
        for mod, mod_data in sid_metrics.get("modalities", {}).items():
            n = mod_data.get("n_rows_extracted", 0)
            total_rows += n
            modality_totals[mod] = modality_totals.get(mod, 0) + n

    global_summary = {
        "total_subjects_processed": len(all_subject_metrics),
        "total_feature_rows": total_rows,
        "rows_per_modality": modality_totals,
        "active_modalities": ACTIVE_MODALITIES,
        "excluded_modalities": ["fnirs"],
    }

    with open(STAGE6_METRICS_DIR / "features_metrics.json", "w") as f:
        json.dump(
            {"subjects": {str(k): v for k, v in all_subject_metrics.items()},
             "global_summary": global_summary},
            f, indent=2,
        )

    if verbose:
        print(f"[Stage 6] Done. {total_rows} total feature rows across {len(all_subject_metrics)} subjects.")
