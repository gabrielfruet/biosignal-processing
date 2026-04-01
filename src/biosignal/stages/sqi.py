"""Stage 2: Signal Quality Index (SQI).

Evaluates signal quality using quantitative metrics including SNR, kurtosis,
spectral entropy, and artifact detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal, stats
from scipy.signal import welch

from biosignal.config import (
    METRICS_DIR,
    FIGURES_DIR,
    SFREQ,
)
from biosignal.io.ieee import load, list_subjects, SubjectDict, ModalityDict


# Modality-specific frequency bands (Hz)
FREQ_BANDS = {
    "eeg": {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "noise": (50, 60),
    },
    "ecg": {"qrs": (10, 20), "noise": (0, 5)},
    "emg": {"burst": (20, 200), "noise": (200, 250)},
    "fnirs": {"hemodynamic": (0.01, 0.1), "noise": (0.5, 2)},
}

# Rejection thresholds per modality (more lenient defaults)
REJECTION_THRESHOLDS = {
    "eeg": {
        "snr_min_db": -5.0,
        "snr_max_db": 50.0,
        "kurtosis_max": 50.0,  # EEG often has high kurtosis due to eye blinks
        "kurtosis_min": -10.0,
        "spectral_entropy_min": 0.15,  # Low = rhythmic (good for EEG)
        "spectral_entropy_max": 0.95,
        "amplitude_iqr_threshold": 5000,  # μV IQR
    },
    "ecg": {
        "snr_min_db": -3.0,
        "snr_max_db": 50.0,
        "kurtosis_max": 100.0,  # ECG spikes (R-peaks) create high kurtosis
        "kurtosis_min": -10.0,
        "spectral_entropy_min": 0.3,
        "spectral_entropy_max": 0.95,
        "amplitude_iqr_threshold": 5,  # mV IQR
    },
    "emg": {
        "snr_min_db": -5.0,
        "snr_max_db": 50.0,
        "kurtosis_max": 50.0,
        "kurtosis_min": -10.0,
        "spectral_entropy_min": 0.2,
        "spectral_entropy_max": 0.98,
        "amplitude_iqr_threshold": 10,  # mV IQR
    },
    "fnirs": {
        "snr_min_db": -50.0,  # Very low SNR is expected for fNIRS
        "snr_max_db": 20.0,
        "kurtosis_max": 100.0,  # Hemodynamic responses create spikes
        "kurtosis_min": -50.0,
        "spectral_entropy_min": 0.01,  # Very low entropy expected (slow signals)
        "spectral_entropy_max": 0.99,
        "amplitude_iqr_threshold": 1.0,  # mM·mm
    },
}

# Global defaults for fallback
DEFAULT_THRESHOLDS = REJECTION_THRESHOLDS["eeg"]

# Physiological limits per modality
PHYSIOLOGICAL_LIMITS = {
    "eeg": {"amplitude_max_uv": 200},
    "ecg": {"hr_min": 40, "hr_max": 200},
    "emg": {"amplitude_max_mv": 5},
    "fnirs": {"conc_max_mm": 0.1},
}


@dataclass
class SQIMetrics:
    """Container for SQI metrics of a single segment."""

    start_s: float
    end_s: float
    snr_db: float
    kurtosis: float
    skewness: float
    spectral_entropy: float
    amplitude_iqr: float
    artifacts: dict[str, bool]
    rejected: bool
    reject_reason: str | None
    outlier_type: str | None  # "physiological" or "instrumental"


def compute_snr(data: np.ndarray, sfreq: int, modality: str) -> float:
    """Calculate Signal-to-Noise Ratio using Welch PSD.

    Args:
        data: Signal segment (1D array).
        sfreq: Sampling frequency in Hz.
        modality: Signal modality for band selection.

    Returns:
        SNR in dB.
    """
    bands = FREQ_BANDS.get(modality, {"signal": (1, 50), "noise": (0, 1)})

    # Compute PSD
    freqs, psd = welch(data, fs=sfreq, nperseg=min(256, len(data)))

    # Find frequency resolution
    freq_res = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0

    # Signal power (sum of PSD in signal bands)
    signal_power = 0.0
    for band_range in bands.values():
        if band_range[0] < sfreq / 2:
            idx = np.logical_and(freqs >= band_range[0], freqs <= band_range[1])
            signal_power += np.sum(psd[idx])

    # Noise power (sum of PSD outside signal bands)
    signal_freqs = set()
    for band_range in bands.values():
        if band_range[0] < sfreq / 2:
            idx = np.logical_and(freqs >= band_range[0], freqs <= band_range[1])
            for i in np.where(idx)[0]:
                signal_freqs.add(i)

    noise_idx = np.array([i for i in range(len(freqs)) if i not in signal_freqs])
    noise_power = np.sum(psd[noise_idx]) if len(noise_idx) > 0 else 1e-10

    # Avoid division by zero
    noise_power = max(noise_power, 1e-10)

    snr_linear = signal_power / noise_power
    snr_db = 10 * np.log10(snr_linear)

    return float(snr_db)


def compute_kurtosis_skewness(data: np.ndarray) -> tuple[float, float]:
    """Compute kurtosis and skewness.

    Args:
        data: Signal segment (1D array).

    Returns:
        Tuple of (kurtosis, skewness).
    """
    # Remove NaN values
    data_clean = data[~np.isnan(data)]

    if len(data_clean) < 4:
        return 0.0, 0.0

    kurt = float(stats.kurtosis(data_clean))
    skew = float(stats.skew(data_clean))

    return kurt, skew


def compute_spectral_entropy(data: np.ndarray, sfreq: int) -> float:
    """Calculate normalized spectral entropy.

    Args:
        data: Signal segment (1D array).
        sfreq: Sampling frequency in Hz.

    Returns:
        Spectral entropy (0-1).
    """
    # Compute power spectrum
    freqs, psd = welch(data, fs=sfreq, nperseg=min(256, len(data)))

    # Normalize PSD to get probability distribution
    psd_norm = psd / (np.sum(psd) + 1e-10)

    # Calculate Shannon entropy
    entropy = -np.sum(psd_norm * np.log2(psd_norm + 1e-10))

    # Normalize by maximum possible entropy (log2 of number of frequency bins)
    n_bins = len(psd)
    max_entropy = np.log2(n_bins) if n_bins > 1 else 1.0

    spectral_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    return float(np.clip(spectral_entropy, 0, 1))


def compute_amplitude_iqr(data: np.ndarray) -> float:
    """Compute amplitude interquartile range.

    Args:
        data: Signal segment (1D array).

    Returns:
        IQR of the signal amplitude.
    """
    q75, q25 = np.percentile(data, [75, 25])
    return float(q75 - q25)


def detect_movement_artifact(data: np.ndarray, sfreq: int) -> bool:
    """Detect movement artifacts based on extreme amplitude changes.

    Args:
        data: Signal segment (1D array).
        sfreq: Sampling frequency in Hz.

    Returns:
        True if movement artifact detected (only for extreme cases).
    """
    # Only flag as movement artifact if amplitude is extremely high
    # This is a conservative check - movement artifacts usually show
    # sudden large amplitude changes
    iqr = compute_amplitude_iqr(data)
    data_range = np.max(data) - np.min(data)

    # Flag if range is >10x IQR (severe saturation or movement)
    if iqr > 0 and data_range / iqr > 10:
        return True

    return False


def detect_loose_electrode(data: np.ndarray, sfreq: int) -> bool:
    """Detect loose electrode based on very low variance.

    Args:
        data: Signal segment (1D array).
        sfreq: Sampling frequency in Hz.

    Returns:
        True if loose electrode artifact detected (only for extreme cases).
    """
    # Very low variance indicates dead channel or loose electrode
    variance = np.var(data)
    data_range = np.max(data) - np.min(data)

    # Flag if variance is essentially zero compared to range
    if data_range > 0 and variance / (data_range**2) < 0.0001:
        return True

    return False


def classify_outlier_type(
    snr_db: float,
    kurtosis: float,
    has_movement: bool,
    has_loose: bool,
) -> str | None:
    """Classify the type of outlier detected.

    Args:
        snr_db: Signal-to-noise ratio in dB.
        kurtosis: Kurtosis value.
        has_movement: Whether movement artifact was detected.
        has_loose: Whether loose electrode was detected.

    Returns:
        "physiological", "instrumental", or None.
    """
    if has_loose or (kurtosis > REJECTION_THRESHOLDS["kurtosis_max"] and snr_db < 5):
        return "instrumental"
    if has_movement or (snr_db > REJECTION_THRESHOLDS["snr_max_db"]):
        return "physiological"
    return None


def compute_sqi_per_segment(
    data: np.ndarray,
    sfreq: int,
    modality: str,
    start_s: float,
    window_s: float,
) -> SQIMetrics:
    """Calculate SQI metrics for a signal segment.

    Args:
        data: Full signal data (1D array).
        sfreq: Sampling frequency in Hz.
        modality: Signal modality.
        start_s: Segment start time in seconds.
        window_s: Window duration in seconds.

    Returns:
        SQIMetrics dataclass with all computed values.
    """
    start_sample = int(start_s * sfreq)
    end_sample = int((start_s + window_s) * sfreq)

    segment = data[start_sample : min(end_sample, len(data))]

    if len(segment) < sfreq * 0.5:  # Less than 0.5s of data
        return SQIMetrics(
            start_s=start_s,
            end_s=start_s + window_s,
            snr_db=0.0,
            kurtosis=0.0,
            skewness=0.0,
            spectral_entropy=0.0,
            amplitude_iqr=0.0,
            artifacts={"movement": False, "loose_electrode": False},
            rejected=True,
            reject_reason="insufficient_data",
            outlier_type=None,
        )

    # Get modality-specific thresholds
    thresholds = REJECTION_THRESHOLDS.get(modality, DEFAULT_THRESHOLDS)

    # Compute metrics
    snr_db = compute_snr(segment, sfreq, modality)
    kurtosis, skewness = compute_kurtosis_skewness(segment)
    spectral_entropy = compute_spectral_entropy(segment, sfreq)
    amplitude_iqr = compute_amplitude_iqr(segment)

    # Artifact detection (with modality-specific sensitivity)
    has_movement = detect_movement_artifact(segment, sfreq)
    has_loose = detect_loose_electrode(segment, sfreq)

    # Amplitude-based rejection (only if extreme)
    extreme_amplitude = amplitude_iqr > thresholds["amplitude_iqr_threshold"]

    # Rejection logic (only for severe issues)
    rejected = False
    reject_reason = None
    outlier_type = None

    # Check thresholds
    if snr_db < thresholds["snr_min_db"]:
        rejected = True
        reject_reason = "low_snr"
        outlier_type = "instrumental"
    elif snr_db > thresholds["snr_max_db"]:
        rejected = True
        reject_reason = "high_snr_suspicious"
        outlier_type = "instrumental"
    elif kurtosis > thresholds["kurtosis_max"]:
        rejected = True
        reject_reason = "high_kurtosis"
        outlier_type = "instrumental"
    elif kurtosis < thresholds["kurtosis_min"]:
        rejected = True
        reject_reason = "low_kurtosis"
        outlier_type = "instrumental"
    elif spectral_entropy < thresholds["spectral_entropy_min"]:
        rejected = True
        reject_reason = "low_spectral_entropy"
        outlier_type = "instrumental"
    elif spectral_entropy > thresholds["spectral_entropy_max"]:
        rejected = True
        reject_reason = "high_spectral_entropy"
        outlier_type = "anomalous"
    elif has_loose and extreme_amplitude:
        # Loose electrode only rejected if combined with extreme amplitude
        rejected = True
        reject_reason = "loose_electrode"
        outlier_type = "instrumental"
    elif has_movement and extreme_amplitude:
        # Movement only rejected if combined with extreme amplitude
        rejected = True
        reject_reason = "movement_artifact"
        outlier_type = "physiological"

    return SQIMetrics(
        start_s=start_s,
        end_s=start_s + window_s,
        snr_db=snr_db,
        kurtosis=kurtosis,
        skewness=skewness,
        spectral_entropy=spectral_entropy,
        amplitude_iqr=amplitude_iqr,
        artifacts={"movement": has_movement, "loose_electrode": has_loose},
        rejected=rejected,
        reject_reason=reject_reason,
        outlier_type=outlier_type,
    )


def plot_sqi_comparison(
    data: np.ndarray,
    sfreq: int,
    modality: str,
    good_segments: list[tuple[float, float]],
    bad_segments: list[tuple[float, float]],
    subject_id: int,
    window_s: float = 5.0,
) -> None:
    """Generate side-by-side comparison of good vs bad segments.

    Args:
        data: Full signal data.
        sfreq: Sampling frequency.
        modality: Signal modality.
        good_segments: List of (start_s, end_s) tuples for good segments.
        bad_segments: List of (start_s, end_s) tuples for bad segments.
        subject_id: Subject ID for filename.
        window_s: Window duration in seconds.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} SQI Comparison",
        fontsize=14,
        fontweight="bold",
    )

    # Select representative segments (first of each type)
    plot_good = good_segments[:2] if good_segments else []
    plot_bad = bad_segments[:2] if bad_segments else []

    all_segments = list(zip(["Good"] * len(plot_good), plot_good)) + list(
        zip(["Bad"] * len(plot_bad), plot_bad)
    )

    if not all_segments:
        axes[0].text(0.5, 0.5, "No segments to display", ha="center", va="center")
        axes[1].text(0.5, 0.5, "No segments to display", ha="center", va="center")
        output_path = FIGURES_DIR / f"sqi_comparison_{subject_id:03d}_{modality}.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return

    # Plot good segments (top)
    ax_good = axes[0]
    for i, (start_s, _) in enumerate(plot_good):
        start_sample = int(start_s * sfreq)
        end_sample = int((start_s + window_s) * sfreq)
        segment = data[start_sample : min(end_sample, len(data))]
        time = np.arange(len(segment)) / sfreq

        label = f"Seg {i + 1} ({start_s:.0f}-{start_s + window_s:.0f}s)"
        ax_good.plot(time, segment, linewidth=0.5, label=label, alpha=0.8)

    ax_good.set_title(f"Good Segments (n={len(plot_good)})")
    ax_good.set_ylabel("Amplitude")
    ax_good.legend(loc="upper right", fontsize=8)
    ax_good.grid(True, alpha=0.3)
    ax_good.set_xlim(0, window_s)

    # Plot bad segments (bottom)
    ax_bad = axes[1]
    for i, (start_s, _) in enumerate(plot_bad):
        start_sample = int(start_s * sfreq)
        end_sample = int((start_s + window_s) * sfreq)
        segment = data[start_sample : min(end_sample, len(data))]
        time = np.arange(len(segment)) / sfreq

        label = f"Seg {i + 1} ({start_s:.0f}-{start_s + window_s:.0f}s)"
        ax_bad.plot(time, segment, linewidth=0.5, label=label, alpha=0.8, color="red")

    ax_bad.set_title(f"Bad Segments (n={len(plot_bad)})")
    ax_bad.set_xlabel("Time (s)")
    ax_bad.set_ylabel("Amplitude")
    ax_bad.legend(loc="upper right", fontsize=8)
    ax_bad.grid(True, alpha=0.3)
    ax_bad.set_xlim(0, window_s)

    output_path = FIGURES_DIR / f"sqi_comparison_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_sqi_heatmap(
    all_sqi_data: dict[int, dict[str, list[dict]]],
    output_path: Path,
) -> None:
    """Generate heatmap of SQI metrics across subjects and modalities.

    Args:
        all_sqi_data: Dictionary of subject_id -> modality -> segment metrics.
        output_path: Path to save the figure.
    """
    subjects = sorted(all_sqi_data.keys())
    modalities = ["eeg", "ecg", "emg", "fnirs"]

    # Calculate mean SNR per subject × modality
    snr_matrix = np.zeros((len(subjects), len(modalities)))
    rejection_matrix = np.zeros((len(subjects), len(modalities)))

    for i, subj_id in enumerate(subjects):
        for j, mod in enumerate(modalities):
            segments = all_sqi_data.get(subj_id, {}).get(mod, [])
            if segments:
                snr_values = [s["snr_db"] for s in segments if "snr_db" in s]
                snr_matrix[i, j] = np.mean(snr_values) if snr_values else np.nan

                rejected_count = sum(1 for s in segments if s.get("rejected", False))
                rejection_matrix[i, j] = rejected_count / len(segments)
            else:
                snr_matrix[i, j] = np.nan
                rejection_matrix[i, j] = np.nan

    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 8), constrained_layout=True)
    fig.suptitle("Signal Quality Index Heatmap", fontsize=14, fontweight="bold")

    # SNR heatmap
    ax1 = axes[0]
    im1 = ax1.imshow(snr_matrix, cmap="RdYlGn", aspect="auto", vmin=-5, vmax=30)
    ax1.set_xticks(range(len(modalities)))
    ax1.set_xticklabels([m.upper() for m in modalities])
    ax1.set_yticks(range(len(subjects)))
    ax1.set_yticklabels([f"S{s:03d}" for s in subjects], fontsize=8)
    ax1.set_title("Mean SNR (dB)")
    plt.colorbar(im1, ax=ax1, label="dB")

    # Add text annotations
    for i in range(len(subjects)):
        for j in range(len(modalities)):
            val = snr_matrix[i, j]
            if not np.isnan(val):
                ax1.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7)

    # Rejection rate heatmap
    ax2 = axes[1]
    im2 = ax2.imshow(rejection_matrix, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=1)
    ax2.set_xticks(range(len(modalities)))
    ax2.set_xticklabels([m.upper() for m in modalities])
    ax2.set_yticks(range(len(subjects)))
    ax2.set_yticklabels([f"S{s:03d}" for s in subjects], fontsize=8)
    ax2.set_title("Rejection Rate")
    plt.colorbar(im2, ax=ax2, label="Rate")

    # Add text annotations
    for i in range(len(subjects)):
        for j in range(len(modalities)):
            val = rejection_matrix[i, j]
            if not np.isnan(val):
                ax2.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7)

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def run(subject_id: int | None = None, verbose: bool = False) -> None:
    """Execute Stage 2 SQI pipeline.

    Args:
        subject_id: Optional specific subject to process. If None, process all.
        verbose: Enable verbose output.
    """
    # Ensure output directories exist
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list_subjects()

    if verbose:
        print("Stage 2: Signal Quality Index (SQI)")
        print(f"Processing {len(subjects)} subjects: {subjects}")

    # Window configuration
    window_s = 5.0

    # Collect all SQI data for heatmap
    all_sqi_data: dict[int, dict[str, list[dict]]] = {}

    # Process each subject
    for subj_id in subjects:
        if verbose:
            print(f"  Processing subject {subj_id:03d}...")

        try:
            data = load(subj_id)
        except FileNotFoundError as e:
            print(f"Warning: Could not load subject {subj_id}: {e}")
            continue

        subject_metrics: dict[str, dict] = {}
        subject_sqi_data: dict[str, list[dict]] = {}

        # Process each modality
        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality not in data:
                continue

            modality_data: ModalityDict = data[modality]
            raw = modality_data["data"]
            sfreq = SFREQ.get(modality, 250)
            raw_data = raw.get_data()[0]  # Get first channel

            # Get signal duration
            duration_s = len(raw_data) / sfreq
            n_windows = int(duration_s / window_s)

            if n_windows == 0:
                continue

            # Compute SQI for each segment
            sqi_metrics: list[dict] = []
            for w in range(n_windows):
                start_s = w * window_s
                metrics = compute_sqi_per_segment(
                    raw_data, sfreq, modality, start_s, window_s
                )
                sqi_metrics.append(asdict(metrics))

            # Separate good and bad segments
            good_segments = [
                (m["start_s"], m["end_s"]) for m in sqi_metrics if not m["rejected"]
            ]
            bad_segments = [
                (m["start_s"], m["end_s"]) for m in sqi_metrics if m["rejected"]
            ]

            # Compute summary statistics
            n_rejected = sum(1 for m in sqi_metrics if m["rejected"])
            n_physiological = sum(
                1 for m in sqi_metrics if m["outlier_type"] == "physiological"
            )
            n_instrumental = sum(
                1 for m in sqi_metrics if m["outlier_type"] == "instrumental"
            )

            summary = {
                "total_segments": len(sqi_metrics),
                "rejected_segments": n_rejected,
                "rejection_rate": n_rejected / len(sqi_metrics) if sqi_metrics else 0,
                "physiological_outliers": n_physiological,
                "instrumental_outliers": n_instrumental,
            }

            subject_metrics[modality] = {
                "segments": sqi_metrics,
                "summary": summary,
            }
            subject_sqi_data[modality] = sqi_metrics

            # Generate comparison plot
            plot_sqi_comparison(
                raw_data,
                sfreq,
                modality,
                good_segments,
                bad_segments,
                subj_id,
                window_s,
            )

            if verbose:
                print(
                    f"    {modality.upper()}: {summary['total_segments']} segments, "
                    f"{summary['rejected_segments']} rejected "
                    f"({summary['rejection_rate']:.1%})"
                )

        all_sqi_data[subj_id] = subject_sqi_data

        # Save per-subject metrics
        metrics_path = METRICS_DIR / f"s{subj_id:03d}_sqi.json"
        with open(metrics_path, "w") as f:
            json.dump(subject_metrics, f, indent=2)

    # Generate global SQI heatmap
    if all_sqi_data:
        heatmap_path = FIGURES_DIR / "sqi_heatmap.png"
        plot_sqi_heatmap(all_sqi_data, heatmap_path)

    # Save aggregated metrics
    aggregate_metrics = {
        "config": {
            "window_size_s": window_s,
            "rejection_thresholds": {
                modality: {
                    k: v for k, v in thresholds.items() if not k.endswith("_threshold")
                }
                for modality, thresholds in REJECTION_THRESHOLDS.items()
            },
        },
        "subjects": {
            subj_id: {
                mod: {
                    "segments": sqi_list,
                    "summary": {
                        "total_segments": len(sqi_list),
                        "rejected_segments": sum(1 for s in sqi_list if s["rejected"]),
                        "rejection_rate": (
                            sum(1 for s in sqi_list if s["rejected"]) / len(sqi_list)
                            if sqi_list
                            else 0
                        ),
                    },
                }
                for mod, sqi_list in mod_data.items()
            }
            for subj_id, mod_data in all_sqi_data.items()
        },
        "global_summary": {
            "subjects_processed": len(all_sqi_data),
            "modalities": ["eeg", "ecg", "emg", "fnirs"],
        },
    }

    metrics_path = METRICS_DIR / "sqi_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(aggregate_metrics, f, indent=2)

    if verbose:
        print(f"\nStage 2 complete!")
        print(f"  Metrics: {METRICS_DIR}")
        print(f"  Figures: {FIGURES_DIR}")
