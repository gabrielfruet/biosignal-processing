"""Stage 5: Segmentation (Windowing).

Implements fixed and event-based segmentation for biosignal data.
Integrates with SQI (Stage 2) for quality-aware windowing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import adfuller

from biosignal.config import (
    STAGE2_METRICS_DIR,
    STAGE5_METRICS_DIR,
    STAGE5_FIGURES_DIR,
    STAGE5_DATA_DIR,
    SFREQ,
    CHANNELS,
    SEGMENTATION_CONFIG,
    EVENT_WINDOW_CONFIG,
)
from biosignal.io.ieee import load, list_subjects, ModalityDict


# Alias for type hints
MarkersDict = dict[str, dict[str, int]]


@dataclass
class WindowMetrics:
    """Container for window-level metrics."""

    window_id: int
    start_s: float
    end_s: float
    start_sample: int
    end_sample: int
    cv: float  # Coefficient of Variation
    variance: float
    adf_stat: float | None  # ADF test statistic
    adf_pvalue: float | None  # ADF p-value
    is_stationary: bool  # True if ADF p < 0.05
    is_stable: bool  # True if CV < threshold
    sqi_rejected: bool
    sqi_reject_reason: str | None


def _window_metrics_to_dict(wm: WindowMetrics) -> dict:
    """Convert WindowMetrics to dict with JSON-serializable types."""
    return {
        "window_id": wm.window_id,
        "start_s": wm.start_s,
        "end_s": wm.end_s,
        "start_sample": wm.start_sample,
        "end_sample": wm.end_sample,
        "cv": float(wm.cv),
        "variance": float(wm.variance),
        "adf_stat": float(wm.adf_stat) if wm.adf_stat is not None else None,
        "adf_pvalue": float(wm.adf_pvalue) if wm.adf_pvalue is not None else None,
        "is_stationary": bool(wm.is_stationary),
        "is_stable": bool(wm.is_stable),
        "sqi_rejected": bool(wm.sqi_rejected),
        "sqi_reject_reason": wm.sqi_reject_reason,
    }


def create_fixed_windows(
    data: np.ndarray,
    sfreq: int,
    window_size_s: float,
    overlap_s: float = 0.0,
) -> tuple[np.ndarray, list[dict]]:
    """Create fixed-size windows from signal data.

    Args:
        data: Signal data (n_channels, n_samples).
        sfreq: Sampling frequency in Hz.
        window_size_s: Window duration in seconds.
        overlap_s: Overlap duration in seconds (0 = no overlap).

    Returns:
        Tuple of (windows array, window metadata list).
        windows: Array of shape (n_windows, n_channels, window_samples)
        metadata: List of dicts with timing info.
    """
    n_channels, n_samples = data.shape
    window_samples = int(window_size_s * sfreq)
    step_samples = window_samples - int(overlap_s * sfreq)

    if step_samples <= 0:
        step_samples = window_samples

    windows = []
    metadata = []

    start_idx = 0
    window_id = 0

    while start_idx + window_samples <= n_samples:
        end_idx = start_idx + window_samples
        window_data = data[:, start_idx:end_idx]

        windows.append(window_data)
        metadata.append(
            {
                "window_id": window_id,
                "start_sample": start_idx,
                "end_sample": end_idx,
                "start_s": start_idx / sfreq,
                "end_s": end_idx / sfreq,
            }
        )

        start_idx += step_samples
        window_id += 1

    if windows:
        windows = np.array(windows)
    else:
        windows = np.array(windows)

    return windows, metadata


def segment_by_markers(
    data: np.ndarray,
    markers: MarkersDict,
    sfreq: int,
    modality: str,
    window_before_s: float = 0,
    window_after_s: float = 30,
) -> dict[str, np.ndarray]:
    """Segment signal based on experimental markers.

    Args:
        data: Signal data (n_channels, n_samples).
        markers: Dictionary with 'baseline', 'stim_start', 'stim_end'.
        sfreq: Sampling frequency in Hz.
        modality: Modality name (used to get marker sample index).
        window_before_s: Seconds before marker.
        window_after_s: Seconds after marker.

    Returns:
        Dictionary with segment labels as keys and window data as values.
    """
    segments = {}

    for event_type in ["baseline", "stimulation", "recovery"]:
        if event_type == "baseline":
            marker_key = "baseline"
        elif event_type == "stimulation":
            marker_key = "stim_start"
        else:
            marker_key = "stim_end"

        if marker_key not in markers:
            continue

        if modality not in markers[marker_key]:
            continue

        marker_sample = markers[marker_key][modality]

        before_samples = int(window_before_s * sfreq)
        after_samples = int(window_after_s * sfreq)

        start_sample = max(0, marker_sample - before_samples)
        end_sample = min(data.shape[1], marker_sample + after_samples)

        segment = data[:, start_sample:end_sample]

        if segment.shape[1] > 0:
            segments[event_type] = segment

    return segments


def load_sqi_rejected(subject_id: int) -> dict[str, list[dict]]:
    """Load SQI rejection information for a subject.

    Args:
        subject_id: Subject ID.

    Returns:
        Dictionary of modality -> list of rejected segment info.
    """
    sqi_path = STAGE2_METRICS_DIR / f"s{subject_id:03d}_sqi.json"

    if not sqi_path.exists():
        return {}

    with open(sqi_path) as f:
        sqi_data = json.load(f)

    rejected = {}

    for modality in ["eeg", "ecg", "emg", "fnirs"]:
        if modality not in sqi_data:
            continue

        segments = sqi_data[modality].get("segments", [])
        rejected_segments = [s for s in segments if s.get("rejected", False)]

        if rejected_segments:
            rejected[modality] = rejected_segments

    return rejected


def filter_windows_by_quality(
    windows: np.ndarray,
    metadata: list[dict],
    sqi_rejected: list[dict],
    sfreq: int,
) -> tuple[np.ndarray, list[dict], np.ndarray]:
    """Filter windows based on SQI rejection info.

    Args:
        windows: Array of windows (n_windows, n_channels, window_samples).
        metadata: Window metadata list.
        sqi_rejected: List of rejected SQI segments.
        sfreq: Sampling frequency.

    Returns:
        Tuple of (filtered_windows, filtered_metadata, rejection_mask).
    """
    if not sqi_rejected or len(windows) == 0:
        return windows, metadata, np.zeros(len(windows), dtype=bool)

    rejection_mask = np.zeros(len(windows), dtype=bool)

    for window_idx, meta in enumerate(metadata):
        start_s = meta["start_s"]
        end_s = meta["end_s"]

        for rejected_seg in sqi_rejected:
            rejected_start = rejected_seg.get("start_s", -1)
            rejected_end = rejected_seg.get("end_s", -1)

            overlap_start = max(start_s, rejected_start)
            overlap_end = min(end_s, rejected_end)

            if overlap_end > overlap_start:
                overlap_duration = overlap_end - overlap_start
                window_duration = end_s - start_s

                if overlap_duration / window_duration > 0.5:
                    rejection_mask[window_idx] = True
                    break

    valid_indices = ~rejection_mask
    valid_windows = windows[valid_indices]
    valid_metadata = [m for m, v in zip(metadata, valid_indices) if v]

    return valid_windows, valid_metadata, rejection_mask


def compute_intra_window_stability(
    windows: np.ndarray,
    metadata: list[dict],
    cv_threshold: float = 0.30,
) -> list[WindowMetrics]:
    """Compute intra-window stability metrics.

    Args:
        windows: Array of windows (n_windows, n_channels, window_samples).
        metadata: Window metadata list.
        cv_threshold: CV threshold for stability (default 0.30 = 30%).

    Returns:
        List of WindowMetrics for each window.
    """
    window_metrics: list[WindowMetrics] = []

    for i, (window, meta) in enumerate(zip(windows, metadata)):
        all_channel_cv = []
        all_channel_var = []

        for ch_idx in range(window.shape[0]):
            ch_data = window[ch_idx]

            mean_val = np.mean(ch_data)
            std_val = np.std(ch_data)

            if mean_val != 0:
                cv = std_val / np.abs(mean_val)
            else:
                cv = 0.0

            all_channel_cv.append(cv)
            all_channel_var.append(np.var(ch_data))

        mean_cv = np.mean(all_channel_cv)
        mean_var = np.mean(all_channel_var)

        try:
            flat_signal = window.flatten()
            adf_result = adfuller(flat_signal[: min(len(flat_signal), 5000)])
            adf_stat = float(adf_result[0])
            adf_pvalue = float(adf_result[1])
            is_stationary = adf_pvalue < 0.05
        except Exception:
            adf_stat = None
            adf_pvalue = None
            is_stationary = False

        is_stable = mean_cv < cv_threshold

        window_metrics.append(
            WindowMetrics(
                window_id=meta["window_id"],
                start_s=meta["start_s"],
                end_s=meta["end_s"],
                start_sample=meta["start_sample"],
                end_sample=meta["end_sample"],
                cv=mean_cv,
                variance=mean_var,
                adf_stat=adf_stat,
                adf_pvalue=adf_pvalue,
                is_stationary=is_stationary,
                is_stable=is_stable,
                sqi_rejected=False,
                sqi_reject_reason=None,
            )
        )

    return window_metrics


def compute_inter_window_variance(
    windows: np.ndarray,
    window_metrics: list[WindowMetrics],
) -> dict:
    """Compute inter-window variance metrics.

    Args:
        windows: Array of windows (n_windows, n_channels, window_samples).
        window_metrics: List of window metrics.

    Returns:
        Dictionary with variance metrics.
    """
    if len(windows) == 0:
        return {
            "between_window_variance": 0.0,
            "mean_cv": 0.0,
            "std_cv": 0.0,
            "n_windows": 0,
        }

    cv_values = [m.cv for m in window_metrics]
    var_values = [m.variance for m in window_metrics]

    if len(cv_values) > 1:
        between_var = np.var(cv_values)
    else:
        between_var = 0.0

    return {
        "between_window_variance": float(between_var),
        "mean_cv": float(np.mean(cv_values)),
        "std_cv": float(np.std(cv_values)),
        "min_cv": float(np.min(cv_values)),
        "max_cv": float(np.max(cv_values)),
        "n_windows": len(windows),
        "n_stable_windows": sum(1 for m in window_metrics if m.is_stable),
        "stability_rate": sum(1 for m in window_metrics if m.is_stable)
        / len(window_metrics)
        if window_metrics
        else 0,
    }


def plot_segmented_windows(
    data: np.ndarray,
    windows: np.ndarray,
    window_metrics: list[WindowMetrics],
    sfreq: int,
    modality: str,
    subject_id: int,
    window_size_s: float,
    n_windows_show: int = 5,
) -> None:
    """Plot segmented windows from signal.

    Args:
        data: Original signal (n_channels, n_samples).
        windows: Window array.
        window_metrics: Window metrics list.
        sfreq: Sampling frequency.
        modality: Modality name.
        subject_id: Subject ID.
        window_size_s: Window size in seconds.
        n_windows_show: Number of windows to display.
    """
    n_channels = min(data.shape[0], 4)
    n_show = min(n_windows_show, len(windows))

    fig, axes = plt.subplots(n_channels, 1, figsize=(14, 3 * n_channels), squeeze=False)
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} Windows "
        f"({window_size_s}s, n={len(windows)})",
        fontsize=14,
        fontweight="bold",
    )

    time_full = np.arange(data.shape[1]) / sfreq

    for ch_idx in range(n_channels):
        ax = axes[ch_idx, 0]

        ch_data = data[ch_idx] * 1e3 if modality in ["ecg", "emg"] else data[ch_idx] * 1e6

        ax.plot(time_full, ch_data, linewidth=0.3, alpha=0.7, color="gray", label="Full")

        colors = plt.cm.viridis(np.linspace(0, 1, n_show))
        for i, (window, metrics) in enumerate(
            zip(windows[:n_show], window_metrics[:n_show])
        ):
            window_time = (
                np.arange(window.shape[1]) / sfreq + metrics.start_s
            )
            window_scaled = window[ch_idx] * 1e3 if modality in ["ecg", "emg"] else window[ch_idx] * 1e6

            alpha = 0.8 if metrics.is_stable else 0.4
            color = "green" if metrics.is_stable else "red"
            ax.plot(window_time, window_scaled, linewidth=0.5, color=colors[i], alpha=alpha)

        ch_name = CHANNELS.get(modality, ["CH"])[ch_idx]
        ax.set_ylabel(f"{ch_name}")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)

    axes[-1, 0].set_xlabel("Time (s)")

    plt.tight_layout()
    output_path = STAGE5_FIGURES_DIR / f"segmentation_windows_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_window_stability(
    window_metrics: list[WindowMetrics],
    modality: str,
    subject_id: int,
) -> None:
    """Plot window stability metrics.

    Args:
        window_metrics: List of window metrics.
        modality: Modality name.
        subject_id: Subject ID.
    """
    if not window_metrics:
        return

    cv_values = [m.cv for m in window_metrics]
    variance_values = [m.variance for m in window_metrics]
    is_stable = [m.is_stable for m in window_metrics]
    is_stationary = [m.is_stationary for m in window_metrics]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} Window Stability",
        fontsize=14,
        fontweight="bold",
    )

    window_ids = range(len(window_metrics))

    ax1 = axes[0, 0]
    ax1.bar(window_ids, cv_values, color=["green" if s else "red" for s in is_stable], alpha=0.7)
    ax1.axhline(y=SEGMENTATION_CONFIG["stability_threshold_cv"], color="orange", linestyle="--", label="Threshold (30%)")
    ax1.set_xlabel("Window ID")
    ax1.set_ylabel("Coefficient of Variation")
    ax1.set_title("CV per Window (Green=Stable)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = axes[0, 1]
    ax2.bar(window_ids, variance_values, color=["blue" if s else "orange" for s in is_stationary], alpha=0.7)
    ax2.set_xlabel("Window ID")
    ax2.set_ylabel("Variance")
    ax2.set_title("Variance per Window (Blue=Stationary)")
    ax2.grid(True, alpha=0.3)

    ax3 = axes[1, 0]
    ax3.hist(cv_values, bins=20, color="steelblue", alpha=0.7, edgecolor="black")
    ax3.axvline(x=np.mean(cv_values), color="red", linestyle="--", label=f"Mean: {np.mean(cv_values):.2f}")
    ax3.set_xlabel("CV")
    ax3.set_ylabel("Count")
    ax3.set_title("CV Distribution")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    n_stable = sum(is_stable)
    n_total = len(window_metrics)
    labels = ["Stable", "Unstable"]
    sizes = [n_stable, n_total - n_stable]
    colors = ["#2ecc71", "#e74c3c"]
    explode = (0.05, 0)

    ax4 = axes[1, 1]
    if sum(sizes) > 0:
        ax4.pie(sizes, explode=explode, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
        ax4.set_title(f"Window Stability Rate: {n_stable}/{n_total}")
    else:
        ax4.text(0.5, 0.5, "No data", ha="center", va="center")

    plt.tight_layout()
    output_path = STAGE5_FIGURES_DIR / f"window_stability_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_inter_window_variance(
    variance_metrics: dict,
    modality: str,
    subject_id: int,
) -> None:
    """Plot inter-window variance summary.

    Args:
        variance_metrics: Variance metrics dict.
        modality: Modality name.
        subject_id: Subject ID.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.suptitle(
        f"Subject {subject_id:03d} - {modality.upper()} Inter-Window Variance",
        fontsize=14,
        fontweight="bold",
    )

    n_windows = variance_metrics.get("n_windows", 0)
    n_stable = variance_metrics.get("n_stable_windows", 0)

    if n_windows == 0:
        axes[0].text(0.5, 0.5, "No windows to analyze", ha="center", va="center", fontsize=12)
        axes[0].axis("off")
        axes[0].set_title("Summary Statistics")

        axes[1].text(0.5, 0.5, "No windows to analyze", ha="center", va="center", fontsize=12)
        axes[1].axis("off")
        axes[1].set_title("Window Stability Count")

        plt.tight_layout()
        output_path = STAGE5_FIGURES_DIR / f"inter_window_variance_{subject_id:03d}_{modality}.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return

    metrics_text = (
        f"Between-Window Variance: {variance_metrics.get('between_window_variance', 0):.4f}\n"
        f"Mean CV: {variance_metrics.get('mean_cv', 0):.4f}\n"
        f"Std CV: {variance_metrics.get('std_cv', 0):.4f}\n"
        f"Min CV: {variance_metrics.get('min_cv', 0):.4f}\n"
        f"Max CV: {variance_metrics.get('max_cv', 0):.4f}\n"
        f"Stability Rate: {variance_metrics.get('stability_rate', 0):.1%}"
    )

    axes[0].text(0.1, 0.5, metrics_text, fontsize=11, family="monospace", verticalalignment="center")
    axes[0].axis("off")
    axes[0].set_title("Summary Statistics")

    labels = ["Stable Windows", "Unstable Windows"]
    sizes = [n_stable, max(0, n_windows - n_stable)]
    colors = ["#2ecc71", "#e74c3c"]

    bars = axes[1].bar(labels, sizes, color=colors, alpha=0.7)
    axes[1].set_ylabel("Count")
    axes[1].set_title("Window Stability Count")
    axes[1].grid(True, alpha=0.3, axis="y")

    max_height = max(sizes) if sizes else 1
    axes[1].set_ylim(0, max_height * 1.2)

    for bar, v in zip(bars, sizes):
        if v > 0:
            axes[1].text(bar.get_x() + bar.get_width() / 2, v + max_height * 0.05, str(v), ha="center", fontweight="bold")

    plt.tight_layout()
    output_path = STAGE5_FIGURES_DIR / f"inter_window_variance_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def run(
    subject_id: int | None = None,
    verbose: bool = False,
    window_size_s: float = 5.0,
    overlap_s: float = 0.0,
) -> None:
    """Execute Stage 5 segmentation pipeline.

    Args:
        subject_id: Optional specific subject to process. If None, process all.
        verbose: Enable verbose output.
        window_size_s: Window duration in seconds (1 or 5).
        overlap_s: Overlap duration in seconds.
    """
    STAGE5_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    STAGE5_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    STAGE5_DATA_DIR.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list_subjects()

    if verbose:
        print("Stage 5: Segmentation (Windowing)")
        print(f"Window size: {window_size_s}s, Overlap: {overlap_s}s")
        print(f"Processing {len(subjects)} subjects: {subjects}")

    cv_threshold = SEGMENTATION_CONFIG["stability_threshold_cv"]
    all_metrics: dict = {"subjects": {}}

    for subj_id in subjects:
        if verbose:
            print(f"  Processing subject {subj_id:03d}...")

        try:
            data = load(subj_id)
        except FileNotFoundError as e:
            print(f"Warning: Could not load subject {subj_id}: {e}")
            continue

        markers = data.get("markers", {})

        try:
            sqi_rejected = load_sqi_rejected(subj_id)
        except Exception:
            sqi_rejected = {}

        subject_metrics: dict = {}
        subject_stability: dict = {}

        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality not in data:
                continue

            modality_data: ModalityDict = data[modality]
            raw = modality_data["data"]
            sfreq = SFREQ.get(modality, 250)

            data_2d = raw.get_data()

            windows, metadata = create_fixed_windows(
                data_2d, sfreq, window_size_s, overlap_s
            )

            rejected_for_mod = sqi_rejected.get(modality, [])
            filtered_windows, filtered_metadata, rejection_mask = filter_windows_by_quality(
                windows, metadata, rejected_for_mod, sfreq
            )

            window_metrics = compute_intra_window_stability(
                filtered_windows, filtered_metadata, cv_threshold
            )

            for i, (wm, was_rejected) in enumerate(zip(window_metrics, rejection_mask)):
                if was_rejected:
                    wm.sqi_rejected = True
                    wm.sqi_reject_reason = "sqi_rejection"

            inter_variance = compute_inter_window_variance(filtered_windows, window_metrics)

            plot_segmented_windows(
                data_2d,
                filtered_windows,
                window_metrics,
                sfreq,
                modality,
                subj_id,
                window_size_s,
            )
            plot_window_stability(window_metrics, modality, subj_id)
            plot_inter_window_variance(inter_variance, modality, subj_id)

            npz_path = STAGE5_DATA_DIR / f"s{subj_id:03d}_{modality}_segments.npz"
            np.savez_compressed(
                npz_path,
                windows=filtered_windows,
                metadata=json.dumps(filtered_metadata),
            )

            subject_metrics[modality] = {
                "n_windows_total": len(windows),
                "n_windows_rejected_sqi": int(np.sum(rejection_mask)),
                "n_windows_usable": len(filtered_windows),
                "windows": [_window_metrics_to_dict(wm) for wm in window_metrics],
            }

            subject_stability[modality] = inter_variance

            if verbose:
                rej_rate = np.sum(rejection_mask) / len(windows) if len(windows) > 0 else 0
                stable_rate = inter_variance.get("stability_rate", 0)
                print(
                    f"    {modality.upper()}: {len(windows)} windows, "
                    f"{np.sum(rejection_mask)} SQI rejected ({rej_rate:.1%}), "
                    f"{inter_variance.get('n_stable_windows', 0)} stable ({stable_rate:.1%})"
                )

        all_metrics["subjects"][str(subj_id)] = {
            "windows": subject_metrics,
            "stability": subject_stability,
        }

        subj_path = STAGE5_METRICS_DIR / f"s{subj_id:03d}_segmentation.json"
        with open(subj_path, "w") as f:
            json.dump(
                {
                    "subject_id": subj_id,
                    "window_size_s": window_size_s,
                    "overlap_s": overlap_s,
                    "metrics": subject_metrics,
                    "stability": subject_stability,
                },
                f,
                indent=2,
            )

    global_summary = _compile_global_summary(all_metrics, cv_threshold)
    all_metrics["global_summary"] = global_summary

    metrics_path = STAGE5_METRICS_DIR / "segmentation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)

    if verbose:
        print(f"\nStage 5 complete!")
        print(f"  Subjects processed: {len(subjects)}")
        print(f"  Window size: {window_size_s}s, Overlap: {overlap_s}s")
        print(f"  Metrics: {STAGE5_METRICS_DIR}")
        print(f"  Figures: {STAGE5_FIGURES_DIR}")
        print(f"  Segments: {STAGE5_DATA_DIR}")
        print(f"  Segments cached: {STAGE5_DATA_DIR}")


def _compile_global_summary(all_metrics: dict, cv_threshold: float) -> dict:
    """Compile global summary statistics."""
    subjects = all_metrics.get("subjects", {})

    total_windows = 0
    total_usable = 0
    total_sqi_rejected = 0
    all_stability_rates = []

    for subj_id, subj_data in subjects.items():
        windows_data = subj_data.get("windows", {})
        stability_data = subj_data.get("stability", {})

        for mod in ["eeg", "ecg", "emg", "fnirs"]:
            if mod in windows_data:
                total_windows += windows_data[mod].get("n_windows_total", 0)
                total_sqi_rejected += windows_data[mod].get("n_windows_rejected_sqi", 0)
                total_usable += windows_data[mod].get("n_windows_usable", 0)

            if mod in stability_data:
                rate = stability_data[mod].get("stability_rate", 0)
                if rate > 0:
                    all_stability_rates.append(rate)

    return {
        "total_subjects": len(subjects),
        "total_windows": total_windows,
        "total_sqi_rejected": total_sqi_rejected,
        "total_usable_windows": total_usable,
        "rejection_rate": total_sqi_rejected / total_windows if total_windows > 0 else 0,
        "mean_stability_rate": float(np.mean(all_stability_rates))
        if all_stability_rates
        else 0,
        "cv_threshold_used": cv_threshold,
    }