"""Stage 4: Data Cleaning & Correction.

Applies filtering, interpolation, and outlier handling to biosignal data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal, stats
from scipy.signal import butter, filtfilt, iirnotch

from biosignal.config import (
    METRICS_DIR,
    FIGURES_DIR,
    DATA_OUT_DIR,
    SFREQ,
    CHANNELS,
)


FILTER_CONFIG = {
    "eeg": {"low_freq": 0.5, "high_freq": 50, "notch_freq": 50, "order": 4},
    "ecg": {"low_freq": 0.5, "high_freq": 50, "notch_freq": 50, "order": 4},
    "emg": {"low_freq": 20, "high_freq": 250, "notch_freq": 50, "order": 4},
    "fnirs": {"low_freq": 0.01, "high_freq": 0.1, "notch_freq": None, "order": 2},
}

WINSORIZE_LIMITS = (0.05, 0.95)
ZSCORE_THRESHOLD = 3.0
MAD_THRESHOLD = 3.5
MAX_INTERPOLATION_GAP_S = 1.0


@dataclass
class CleaningMetrics:
    """Container for cleaning metrics."""

    modality: str
    n_samples_before: int
    n_samples_after: int
    samples_interpolated: int
    samples_winsorized: int
    variance_before: float
    variance_after: float
    kurtosis_before: float
    kurtosis_after: float
    snr_before_db: float
    snr_after_db: float
    cohens_d: float
    effect_size_interpretation: str


def _butter_bandpass(low: float, high: float, sfreq: int, order: int) -> tuple | None:
    """Design Butterworth band-pass filter.

    Returns None if frequencies are invalid.
    """
    nyq = sfreq / 2
    low_norm = low / nyq
    high_norm = high / nyq

    if low_norm <= 0 or high_norm >= 1 or low_norm >= high_norm:
        return None

    b, a = butter(order, [low_norm, high_norm], btype="band")
    return b, a


def _butter_lowpass(high: float, sfreq: int, order: int) -> tuple | None:
    """Design Butterworth low-pass filter.

    Returns None if frequency is invalid.
    """
    nyq = sfreq / 2
    high_norm = high / nyq

    if high_norm <= 0 or high_norm >= 1:
        return None

    b, a = butter(order, high_norm, btype="low")
    return b, a


def _butter_highpass(low: float, sfreq: int, order: int) -> tuple | None:
    """Design Butterworth high-pass filter.

    Returns None if frequency is invalid.
    """
    nyq = sfreq / 2
    low_norm = low / nyq

    if low_norm <= 0 or low_norm >= 1:
        return None

    b, a = butter(order, low_norm, btype="high")
    return b, a


def apply_bandpass_filter(
    data: np.ndarray, sfreq: int, low: float, high: float, order: int = 4
) -> np.ndarray:
    """Apply band-pass filter with safe fallback.

    Args:
        data: Input signal (1D).
        sfreq: Sampling frequency.
        low: Low cutoff frequency.
        high: High cutoff frequency.
        order: Filter order.

    Returns:
        Filtered signal, or original if filtering fails.
    """
    result = _butter_bandpass(low, high, sfreq, order)
    if result is None:
        return data

    b, a = result
    try:
        return filtfilt(b, a, data)
    except Exception:
        return data


def apply_lowpass_filter(
    data: np.ndarray, sfreq: int, high: float, order: int = 4
) -> np.ndarray:
    """Apply low-pass filter with safe fallback."""
    result = _butter_lowpass(high, sfreq, order)
    if result is None:
        return data

    b, a = result
    try:
        return filtfilt(b, a, data)
    except Exception:
        return data


def apply_highpass_filter(
    data: np.ndarray, sfreq: int, low: float, order: int = 4
) -> np.ndarray:
    """Apply high-pass filter with safe fallback."""
    result = _butter_highpass(low, sfreq, order)
    if result is None:
        return data

    b, a = result
    try:
        return filtfilt(b, a, data)
    except Exception:
        return data


def apply_bandpass_filter(
    data: np.ndarray, sfreq: int, low: float, high: float, order: int = 4
) -> np.ndarray:
    """Apply band-pass filter.

    Args:
        data: Input signal (1D).
        sfreq: Sampling frequency.
        low: Low cutoff frequency.
        high: High cutoff frequency.
        order: Filter order.

    Returns:
        Filtered signal.
    """
    b, a = _butter_bandpass(low, high, sfreq, order)
    return filtfilt(b, a, data)


def apply_lowpass_filter(
    data: np.ndarray, sfreq: int, high: float, order: int = 4
) -> np.ndarray:
    """Apply low-pass filter."""
    b, a = _butter_lowpass(high, sfreq, order)
    return filtfilt(b, a, data)


def apply_highpass_filter(
    data: np.ndarray, sfreq: int, low: float, order: int = 4
) -> np.ndarray:
    """Apply high-pass filter."""
    b, a = _butter_highpass(low, sfreq, order)
    return filtfilt(b, a, data)


def compute_snr_db(data: np.ndarray, sfreq: int) -> float:
    """Estimate SNR in dB using variance ratio method.

    Args:
        data: Input signal.
        sfreq: Sampling frequency.

    Returns:
        Estimated SNR in dB.
    """
    variance = np.var(data)
    if variance < 1e-10:
        return -60.0

    median_abs_dev = np.median(np.abs(data - np.median(data)))
    noise_variance_estimate = (median_abs_dev / 0.6745) ** 2

    if noise_variance_estimate < 1e-10:
        return 30.0

    snr_linear = variance / noise_variance_estimate
    return float(10 * np.log10(snr_linear))


def detect_gaps(data: np.ndarray, threshold: float = 1e-6) -> list[tuple[int, int]]:
    """Detect gap regions where signal is constant.

    Args:
        data: Input signal.
        threshold: Difference threshold to detect flat regions.

    Returns:
        List of (start, end) indices for each gap.
    """
    diff = np.abs(np.diff(data))
    gap_mask = diff < threshold

    gaps = []
    in_gap = False
    start = 0

    for i, is_gap in enumerate(gap_mask):
        if is_gap and not in_gap:
            start = i
            in_gap = True
        elif not is_gap and in_gap:
            if i - start > 5:
                gaps.append((start, i))
            in_gap = False

    if in_gap:
        gaps.append((start, len(data)))

    return gaps


def interpolate_gaps(
    data: np.ndarray, gaps: list[tuple[int, int]], sfreq: int
) -> tuple[np.ndarray, int]:
    """Interpolate short gaps in signal.

    Args:
        data: Input signal.
        gaps: List of (start, end) gap indices.
        sfreq: Sampling frequency.

    Returns:
        Tuple of (interpolated data, total samples interpolated).
    """
    data_clean = data.copy()
    total_interpolated = 0

    max_gap_samples = int(MAX_INTERPOLATION_GAP_S * sfreq)

    for start, end in gaps:
        gap_len = end - start
        if gap_len <= max_gap_samples and gap_len > 5:
            start_idx = max(0, start - 1)
            end_idx = min(len(data) - 1, end)

            if start_idx >= end_idx:
                continue

            interp_len = end - start
            x_new = np.linspace(start_idx, end_idx, interp_len)

            y_known = np.array([data[start_idx], data[end_idx]])
            x_known = np.array([start_idx, end_idx])

            y_interp = np.interp(x_new, x_known, y_known)

            data_clean[start:end] = y_interp
            total_interpolated += gap_len

    return data_clean, total_interpolated


def winsorize(
    data: np.ndarray, limits: tuple[float, float] = WINSORIZE_LIMITS
) -> tuple[np.ndarray, int]:
    """Apply Winsorization to handle extreme outliers.

    Args:
        data: Input signal.
        limits: Percentile limits (lower, upper).

    Returns:
        Tuple of (winsorized data, count of modified samples).
    """
    lower = np.percentile(data, limits[0] * 100)
    upper = np.percentile(data, limits[1] * 100)

    data_ws = data.copy()
    mask_low = data_ws < lower
    mask_high = data_ws > upper
    modified = np.sum(mask_low) + np.sum(mask_high)

    data_ws[mask_low] = lower
    data_ws[mask_high] = upper

    return data_ws, int(modified)


def zscore_rejection(
    data: np.ndarray, threshold: float = ZSCORE_THRESHOLD
) -> tuple[np.ndarray, list[int]]:
    """Apply z-score based outlier rejection with clipping.

    Args:
        data: Input signal.
        threshold: Z-score threshold.

    Returns:
        Tuple of (rejected/corrected data, indices of rejected samples).
    """
    z_scores = np.abs(stats.zscore(data))
    rejected_indices = np.where(z_scores > threshold)[0]

    data_clean = data.copy()
    if len(rejected_indices) > 0:
        median_val = np.median(data)
        mad = np.median(np.abs(data - median_val))
        if mad > 0:
            modified_values = median_val + threshold * mad * np.sign(
                data[rejected_indices] - median_val
            )
            data_clean[rejected_indices] = modified_values

    return data_clean, rejected_indices.tolist()


def mad_based_rejection(
    data: np.ndarray, threshold: float = MAD_THRESHOLD
) -> tuple[np.ndarray, list[int]]:
    """Apply MAD-based outlier rejection with clipping.

    Args:
        data: Input signal.
        threshold: MAD threshold multiplier.

    Returns:
        Tuple of (rejected/corrected data, indices of rejected samples).
    """
    median_val = np.median(data)
    mad = np.median(np.abs(data - median_val))

    if mad < 1e-10:
        return data, []

    deviations = np.abs(data - median_val) / mad
    rejected_indices = np.where(deviations > threshold)[0]

    data_clean = data.copy()
    if len(rejected_indices) > 0:
        data_clean[rejected_indices] = median_val

    return data_clean, rejected_indices.tolist()


def compute_cohens_d(before: np.ndarray, after: np.ndarray) -> float:
    """Compute Cohen's d effect size between before and after.

    Args:
        before: Signal before cleaning.
        after: Signal after cleaning.

    Returns:
        Cohen's d value.
    """
    n1, n2 = len(before), len(after)
    if n1 < 2 or n2 < 2:
        return 0.0

    var1, var2 = np.var(before, ddof=1), np.var(after, ddof=1)
    mean1, mean2 = np.mean(before), np.mean(after)

    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std < 1e-10:
        return 0.0

    return float((mean1 - mean2) / pooled_std)


def interpret_effect_size(d: float) -> str:
    """Interpret Cohen's d effect size."""
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    elif d_abs < 0.5:
        return "small"
    elif d_abs < 0.8:
        return "medium"
    else:
        return "large"


def clean_modality(
    data: np.ndarray, sfreq: int, modality: str
) -> tuple[np.ndarray, dict]:
    """Apply complete cleaning pipeline to a modality.

    Args:
        data: Input signal (n_channels, n_samples).
        sfreq: Sampling frequency.
        modality: Modality name.

    Returns:
        Tuple of (cleaned data, cleaning metrics dict).
    """
    config = FILTER_CONFIG.get(modality, FILTER_CONFIG["eeg"])
    cleaned = data.copy()
    metrics_detail = {
        "channels": {},
        "total_samples_interpolated": 0,
        "total_samples_winsorized": 0,
    }

    for ch_idx in range(cleaned.shape[0]):
        ch_data = cleaned[ch_idx]

        var_before = float(np.var(ch_data))
        kurt_before = float(stats.kurtosis(ch_data))
        snr_before = compute_snr_db(ch_data, sfreq)

        gap_samples = 0
        ws_samples = 0

        if config.get("notch_freq"):
            try:
                ch_data = apply_notch_filter(ch_data, sfreq, config["notch_freq"])
            except Exception:
                pass

        try:
            ch_data = apply_bandpass_filter(
                ch_data, sfreq, config["low_freq"], config["high_freq"], config["order"]
            )
        except Exception:
            try:
                low = config["low_freq"]
                high = config["high_freq"]
                if low > 0.01:
                    ch_data = apply_highpass_filter(
                        ch_data, sfreq, low, config["order"]
                    )
                if high < sfreq / 2 - 1:
                    ch_data = apply_lowpass_filter(
                        ch_data, sfreq, high, config["order"]
                    )
            except Exception:
                pass

        gaps = detect_gaps(ch_data)
        if gaps:
            ch_data, gap_samples = interpolate_gaps(ch_data, gaps, sfreq)

        ch_data, ws_samples = winsorize(ch_data)

        ch_data, _ = zscore_rejection(ch_data)

        var_after = float(np.var(ch_data))
        kurt_after = float(stats.kurtosis(ch_data))
        snr_after = compute_snr_db(ch_data, sfreq)

        d = compute_cohens_d(data[ch_idx], ch_data)

        ch_name = (
            CHANNELS.get(modality, ["CH"])[ch_idx]
            if ch_idx < len(CHANNELS.get(modality, ["CH"]))
            else f"CH{ch_idx}"
        )

        metrics_detail["channels"][ch_name] = {
            "variance_before": var_before,
            "variance_after": var_after,
            "variance_reduction_pct": ((var_before - var_after) / var_before * 100)
            if var_before > 0
            else 0,
            "kurtosis_before": kurt_before,
            "kurtosis_after": kurt_after,
            "snr_before_db": snr_before,
            "snr_after_db": snr_after,
            "snr_improvement_db": snr_after - snr_before,
            "cohens_d": d,
            "effect_interpretation": interpret_effect_size(d),
            "samples_interpolated": gap_samples,
            "samples_winsorized": ws_samples,
        }

        metrics_detail["total_samples_interpolated"] += gap_samples
        metrics_detail["total_samples_winsorized"] += ws_samples

        cleaned[ch_idx] = ch_data

    return cleaned, metrics_detail


def plot_before_after(
    data_before: np.ndarray,
    data_after: np.ndarray,
    sfreq: int,
    modality: str,
    subject_id: int,
) -> None:
    """Generate before/after comparison plot.

    Args:
        data_before: Raw signal.
        data_after: Cleaned signal.
        sfreq: Sampling frequency.
        modality: Modality name.
        subject_id: Subject ID.
    """
    duration = 5
    n_samples = min(int(duration * sfreq), data_before.shape[1])

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} Before/After Cleaning",
        fontsize=14,
        fontweight="bold",
    )

    time = np.arange(n_samples) / sfreq

    for ax_idx, (data, title) in enumerate(
        [(data_before, "Before"), (data_after, "After")]
    ):
        ax = axes[ax_idx]
        for ch_idx in range(data.shape[0]):
            ch_data = data[ch_idx, :n_samples]
            scaling = 1e3 if modality in ["ecg", "emg"] else 1e6
            unit_suffix = "mV" if modality in ["ecg", "emg"] else "μV"
            offset = ch_idx * np.max(np.std(ch_data[:n_samples])) * 3
            ax.plot(
                time,
                ch_data[:n_samples] * scaling + offset,
                linewidth=0.5,
                label=f"CH{ch_idx}",
            )
        ax.set_ylabel(f"Amplitude ({unit_suffix}) + offset")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)
        ax.set_xlim(time[0], time[-1])

    axes[-1].set_xlabel("Time (s)")

    output_path = FIGURES_DIR / f"cleaning_comparison_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_spectrum_comparison(
    data_before: np.ndarray,
    data_after: np.ndarray,
    sfreq: int,
    modality: str,
    subject_id: int,
) -> None:
    """Generate spectral density comparison plot.

    Args:
        data_before: Raw signal.
        data_after: Cleaned signal.
        sfreq: Sampling frequency.
        modality: Modality name.
        subject_id: Subject ID.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} Spectrum Comparison",
        fontsize=14,
        fontweight="bold",
    )

    config = FILTER_CONFIG.get(modality, {})
    freq_range = (0, min(config.get("high_freq", 50) * 2, sfreq / 2))

    for ax_idx, (data, title) in enumerate(
        [(data_before, "Before"), (data_after, "After")]
    ):
        ax = axes[ax_idx]
        for ch_idx in range(min(data.shape[0], 3)):
            ch_data = data[ch_idx]
            freqs, psd = signal.welch(ch_data, fs=sfreq, nperseg=min(256, len(ch_data)))
            ax.semilogy(freqs, psd, linewidth=0.8, label=f"CH{ch_idx}")

        ax.set_xlim(freq_range)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("PSD")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)

    output_path = FIGURES_DIR / f"cleaning_spectrum_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_dist_comparison(
    data_before: np.ndarray,
    data_after: np.ndarray,
    modality: str,
    subject_id: int,
) -> None:
    """Generate distribution comparison histogram.

    Args:
        data_before: Raw signal.
        data_after: Cleaned signal.
        modality: Modality name.
        subject_id: Subject ID.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} Distribution Comparison",
        fontsize=14,
        fontweight="bold",
    )

    for ax_idx, (data, title) in enumerate(
        [(data_before, "Before"), (data_after, "After")]
    ):
        ax = axes[ax_idx]
        for ch_idx in range(min(data.shape[0], 3)):
            ch_data = data[ch_idx]
            ch_data_clean = ch_data[~np.isnan(ch_data)]
            if len(ch_data_clean) > 100:
                ax.hist(
                    ch_data_clean, bins=50, alpha=0.5, label=f"CH{ch_idx}", density=True
                )

        ax.set_xlabel("Amplitude")
        ax.set_ylabel("Density")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)

    output_path = FIGURES_DIR / f"cleaning_dist_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def run(subject_id: int | None = None, verbose: bool = False) -> None:
    """Execute Stage 4 cleaning pipeline.

    Args:
        subject_id: Optional specific subject to process. If None, process all.
        verbose: Enable verbose output.
    """
    from biosignal.io.ieee import load, list_subjects, ModalityDict

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_OUT_DIR.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list_subjects()

    if verbose:
        print("Stage 4: Data Cleaning & Correction")
        print(f"Processing {len(subjects)} subjects: {subjects}")

    all_metrics: dict = {"subjects": {}}

    for subj_id in subjects:
        if verbose:
            print(f"  Processing subject {subj_id:03d}...")

        try:
            data = load(subj_id)
        except FileNotFoundError as e:
            print(f"Warning: Could not load subject {subj_id}: {e}")
            continue

        subject_metrics: dict = {}

        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality not in data:
                continue

            modality_data: ModalityDict = data[modality]
            raw = modality_data["data"]
            sfreq = SFREQ.get(modality, 250)

            data_before = raw.get_data()
            data_after, metrics_detail = clean_modality(data_before, sfreq, modality)

            subject_metrics[modality] = {
                "n_samples_before": int(data_before.shape[1]),
                "n_samples_after": int(data_after.shape[1]),
                "channels": metrics_detail["channels"],
                "total_samples_interpolated": metrics_detail[
                    "total_samples_interpolated"
                ],
                "total_samples_winsorized": metrics_detail["total_samples_winsorized"],
            }

            plot_before_after(data_before, data_after, sfreq, modality, subj_id)
            plot_spectrum_comparison(data_before, data_after, sfreq, modality, subj_id)
            plot_dist_comparison(data_before, data_after, modality, subj_id)

            if verbose:
                ch_count = len(metrics_detail["channels"])
                print(f"    {modality.upper()}: {ch_count} channels cleaned")

        all_metrics["subjects"][str(subj_id)] = subject_metrics

        subject_metrics_path = METRICS_DIR / f"s{subj_id:03d}_cleaning.json"
        with open(subject_metrics_path, "w") as f:
            json.dump(subject_metrics, f, indent=2)

    global_summary = _compile_global_summary(all_metrics)
    all_metrics["global_summary"] = global_summary

    metrics_path = METRICS_DIR / "cleaning_validation.json"
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)

    if verbose:
        print(f"\nStage 4 complete!")
        print(f"  Subjects processed: {len(subjects)}")
        print(f"  Metrics: {METRICS_DIR}")


def _compile_global_summary(all_metrics: dict) -> dict:
    """Compile global summary statistics."""
    subjects = all_metrics.get("subjects", {})

    total_interpolated = 0
    total_winsorized = 0
    snr_improvements = []

    for subj_id, subj_data in subjects.items():
        for mod, mod_data in subj_data.items():
            total_interpolated += mod_data.get("total_samples_interpolated", 0)
            total_winsorized += mod_data.get("total_samples_winsorized", 0)
            for ch, ch_data in mod_data.get("channels", {}).items():
                snr_imp = ch_data.get("snr_improvement_db", 0)
                if snr_imp != 0:
                    snr_improvements.append(snr_imp)

    return {
        "total_subjects": len(subjects),
        "total_samples_interpolated": total_interpolated,
        "total_samples_winsorized": total_winsorized,
        "mean_snr_improvement_db": float(np.mean(snr_improvements))
        if snr_improvements
        else 0,
        "std_snr_improvement_db": float(np.std(snr_improvements))
        if snr_improvements
        else 0,
    }
