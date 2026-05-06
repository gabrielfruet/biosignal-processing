"""Stage 3: Statistical Analysis.

Performs comprehensive statistical analysis on biosignal data including:
- Descriptive statistics (mean, median, variance, SD)
- Quartiles and IQR
- Normality tests (Shapiro-Wilk, Kolmogorov-Smirnov)
- Homoscedasticity tests (Levene, Bartlett)
- Visualizations (histograms, boxplots, Q-Q plots, correlation heatmap)
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from biosignal.config import (
    METRICS_DIR,
    FIGURES_DIR,
    SFREQ,
    CHANNELS,
)
from biosignal.io.ieee import load, list_subjects, SubjectDict, ModalityDict


# Maximum samples for normality tests (scipy limitation)
MAX_NORMality_SAMPLES = 5000

# Window size for segment-level analysis (consistent with SQI)
WINDOW_S = 5.0


def compute_descriptive_stats(data: np.ndarray) -> dict:
    """Compute descriptive statistics for a signal.

    Args:
        data: 1D signal array.

    Returns:
        Dictionary with mean, median, variance, std, min, max, range, skewness, kurtosis.
    """
    # Remove NaN values
    data_clean = data[~np.isnan(data)]

    if len(data_clean) < 2:
        return {
            "mean": None,
            "median": None,
            "variance": None,
            "std": None,
            "min": None,
            "max": None,
            "range": None,
            "skewness": None,
            "kurtosis": None,
            "n_samples": len(data_clean),
        }

    return {
        "mean": float(np.mean(data_clean)),
        "median": float(np.median(data_clean)),
        "variance": float(np.var(data_clean, ddof=1)),
        "std": float(np.std(data_clean, ddof=1)),
        "min": float(np.min(data_clean)),
        "max": float(np.max(data_clean)),
        "range": float(np.max(data_clean) - np.min(data_clean)),
        "skewness": float(stats.skew(data_clean)),
        "kurtosis": float(stats.kurtosis(data_clean)),
        "n_samples": len(data_clean),
    }


def compute_quartiles(data: np.ndarray) -> dict:
    """Compute quartiles and percentiles for a signal.

    Args:
        data: 1D signal array.

    Returns:
        Dictionary with q1, q2 (median), q3, iqr, and percentiles (10, 25, 50, 75, 90).
    """
    data_clean = data[~np.isnan(data)]

    if len(data_clean) < 4:
        return {
            "q1": None,
            "q2": None,
            "q3": None,
            "iqr": None,
            "percentile_10": None,
            "percentile_25": None,
            "percentile_50": None,
            "percentile_75": None,
            "percentile_90": None,
            "n_samples": len(data_clean),
        }

    q1 = float(np.percentile(data_clean, 25))
    q2 = float(np.percentile(data_clean, 50))
    q3 = float(np.percentile(data_clean, 75))

    return {
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "iqr": float(q3 - q1),
        "percentile_10": float(np.percentile(data_clean, 10)),
        "percentile_25": q1,
        "percentile_50": q2,
        "percentile_75": q3,
        "percentile_90": float(np.percentile(data_clean, 90)),
        "n_samples": len(data_clean),
    }


def test_normality(data: np.ndarray) -> dict:
    """Apply normality tests to signal data.

    Args:
        data: 1D signal array.

    Returns:
        Dictionary with Shapiro-Wilk and K-S test results, and is_normal flag.
    """
    data_clean = data[~np.isnan(data)]

    if len(data_clean) < 3:
        return {
            "shapiro_wilk": {
                "stat": None,
                "p_value": None,
                "note": "insufficient_data",
            },
            "ks_test": {"stat": None, "p_value": None, "note": "insufficient_data"},
            "is_normal": None,
            "interpretation": "Insufficient data for normality testing (n < 3)",
            "n_samples": len(data_clean),
        }

    # Shapiro-Wilk test (max 5000 samples due to scipy limitation)
    sample_size = min(len(data_clean), MAX_NORMality_SAMPLES)
    sample = data_clean[:sample_size] if len(data_clean) > sample_size else data_clean

    shapiro_stat, shapiro_p = stats.shapiro(sample)

    # Kolmogorov-Smirnov test (against normal distribution)
    mean_val = np.mean(data_clean)
    std_val = np.std(data_clean)
    if std_val > 0:
        standardized = (data_clean - mean_val) / std_val
        ks_stat, ks_p = stats.kstest(standardized, "norm")
    else:
        ks_stat, ks_p = None, None

    # Combined interpretation (p > 0.05 suggests normality)
    alpha = 0.05
    shapiro_normal = shapiro_p > alpha if shapiro_p is not None else None
    ks_normal = ks_p > alpha if ks_p is not None else None

    # Use Shapiro-Wilk as primary (more powerful for small samples)
    is_normal = shapiro_normal

    # Interpretation
    if is_normal:
        interpretation = (
            "Data appears normally distributed based on Shapiro-Wilk test (p > 0.05)"
        )
    else:
        interpretation = "Data deviates from normal distribution based on Shapiro-Wilk test (p <= 0.05)"

    return {
        "shapiro_wilk": {
            "stat": float(shapiro_stat),
            "p_value": float(shapiro_p),
        },
        "ks_test": {
            "stat": float(ks_stat) if ks_stat is not None else None,
            "p_value": float(ks_p) if ks_p is not None else None,
        },
        "is_normal": bool(is_normal) if is_normal is not None else None,
        "interpretation": interpretation,
        "n_samples": len(data_clean),
    }


def test_homoscedasticity(data_groups: list[np.ndarray]) -> dict:
    """Test homoscedasticity across multiple groups.

    Args:
        data_groups: List of 1D arrays (one per group).

    Returns:
        Dictionary with Levene and Bartlett test results, and is_homoscedastic flag.
    """
    # Filter out empty or invalid groups
    valid_groups = [g[~np.isnan(g)] for g in data_groups if len(g[~np.isnan(g)]) >= 2]

    if len(valid_groups) < 2:
        return {
            "levene": {"stat": None, "p_value": None, "note": "insufficient_groups"},
            "bartlett": {"stat": None, "p_value": None, "note": "insufficient_groups"},
            "is_homoscedastic": None,
            "interpretation": "Insufficient groups for homoscedasticity testing (n < 2)",
            "n_groups": len(valid_groups),
        }

    # Levene's test (more robust to non-normality)
    levene_stat, levene_p = stats.levene(*valid_groups)

    # Bartlett's test (more powerful but assumes normality)
    bartlett_stat, bartlett_p = stats.bartlett(*valid_groups)

    alpha = 0.05
    is_homoscedastic = levene_p > alpha

    if is_homoscedastic:
        interpretation = (
            "Variances appear equal across groups based on Levene's test (p > 0.05)"
        )
    else:
        interpretation = "Variances differ significantly across groups based on Levene's test (p <= 0.05)"

    return {
        "levene": {
            "stat": float(levene_stat),
            "p_value": float(levene_p),
        },
        "bartlett": {
            "stat": float(bartlett_stat),
            "p_value": float(bartlett_p),
        },
        "is_homoscedastic": bool(is_homoscedastic),
        "interpretation": interpretation,
        "n_groups": len(valid_groups),
    }


def plot_histogram(
    data: np.ndarray,
    modality: str,
    channel: str,
    subject_id: int,
    bins: int = 50,
) -> None:
    """Generate histogram with normal curve overlay.

    Args:
        data: 1D signal array.
        modality: Signal modality.
        channel: Channel name.
        subject_id: Subject ID.
        bins: Number of histogram bins.
    """
    data_clean = data[~np.isnan(data)]

    if len(data_clean) < 10:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histogram
    ax.hist(
        data_clean,
        bins=bins,
        density=True,
        alpha=0.7,
        color="steelblue",
        edgecolor="white",
    )

    # Overlay normal distribution
    mean_val = np.mean(data_clean)
    std_val = np.std(data_clean)
    x = np.linspace(data_clean.min(), data_clean.max(), 100)
    normal_curve = stats.norm.pdf(x, mean_val, std_val)
    ax.plot(x, normal_curve, "r-", linewidth=2, label="Normal fit")

    # Labels and title
    ax.set_xlabel("Amplitude")
    ax.set_ylabel("Density")
    ax.set_title(
        f"{modality.upper()} - {channel} - Subject {subject_id:03d}\nHistogram with Normal Distribution"
    )
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Save figure
    output_path = (
        FIGURES_DIR / f"stat_histogram_{subject_id:03d}_{modality}_{channel}.png"
    )
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_boxplot(
    data_per_channel: dict[str, np.ndarray],
    modality: str,
    subject_id: int,
) -> None:
    """Generate boxplot showing distribution across channels.

    Args:
        data_per_channel: Dictionary mapping channel names to data arrays.
        modality: Signal modality.
        subject_id: Subject ID.
    """
    if not data_per_channel:
        return

    # Prepare data for boxplot
    channels = sorted(data_per_channel.keys())
    data_list = [
        data_per_channel[ch][~np.isnan(data_per_channel[ch])] for ch in channels
    ]

    # Filter out empty channels
    valid_data = [(ch, d) for ch, d in zip(channels, data_list) if len(d) >= 3]
    if not valid_data:
        return

    valid_channels = [v[0] for v in valid_data]
    valid_data_arrays = [v[1] for v in valid_data]

    fig, ax = plt.subplots(figsize=(12, 12))

    bp = ax.boxplot(valid_data_arrays, labels=valid_channels, patch_artist=True)

    # Style the boxplot
    for patch in bp["boxes"]:
        patch.set_facecolor("steelblue")
        patch.set_alpha(0.7)
    for median in bp["medians"]:
        median.set_color("red")
        median.set_linewidth(2)

    ax.set_xlabel("Channel")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"{modality.upper()} - Subject {subject_id:03d}\nBoxplot by Channel")
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=45)

    # Save figure
    output_path = FIGURES_DIR / f"stat_boxplot_{subject_id:03d}_{modality}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_qq(
    data: np.ndarray,
    modality: str,
    channel: str,
    subject_id: int,
) -> None:
    """Generate Q-Q plot for normality assessment.

    Args:
        data: 1D signal array.
        modality: Signal modality.
        channel: Channel name.
        subject_id: Subject ID.
    """
    data_clean = data[~np.isnan(data)]

    if len(data_clean) < 10:
        return

    fig, ax = plt.subplots(figsize=(8, 8))

    # Q-Q plot
    stats.probplot(data_clean, dist="norm", plot=ax)

    ax.set_title(
        f"{modality.upper()} - {channel} - Subject {subject_id:03d}\nQ-Q Plot (Normality Check)"
    )
    ax.grid(True, alpha=0.3)

    # Save figure
    output_path = FIGURES_DIR / f"stat_qq_{subject_id:03d}_{modality}_{channel}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_correlation_heatmap(
    all_data: dict[str, np.ndarray],
    subject_id: int,
) -> None:
    """Generate correlation heatmap across modalities/channels.

    Args:
        all_data: Dictionary mapping signal identifiers to data arrays.
        subject_id: Subject ID.
    """
    if not all_data:
        return

    # Compute correlation matrix
    identifiers = sorted(all_data.keys())
    n = len(identifiers)

    if n < 2:
        return

    # Build data matrix (transpose so each row is a channel)
    valid_data = {}
    for ident in identifiers:
        data = all_data[ident]
        data_clean = data[~np.isnan(data)]
        if len(data_clean) >= 10:
            valid_data[ident] = data_clean

    if len(valid_data) < 2:
        return

    valid_ids = list(valid_data.keys())
    n = len(valid_ids)

    # Resample to common length
    min_len = min(len(v) for v in valid_data.values())
    data_matrix = np.array([valid_data[v][:min_len] for v in valid_ids])

    # Compute correlation matrix
    corr_matrix = np.corrcoef(data_matrix)

    # Create heatmap - hide upper triangle including diagonal
    fig, ax = plt.subplots(figsize=(max(8, n * 0.9), max(6, n * 0.8)))

    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    im = ax.imshow(
        np.where(mask, np.nan, corr_matrix),
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        aspect="auto",
    )

    # Set ticks and labels
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(valid_ids, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(valid_ids, fontsize=8)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Correlation Coefficient")

    # Add text annotations for lower triangle including diagonal
    for i in range(n):
        for j in range(i + 1):
            val = corr_matrix[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(
                j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7
            )

    ax.set_title(
        f"Subject {subject_id:03d} - Correlation Heatmap\n(Across Modalities/Channels)"
    )
    ax.set_xlabel("Signal")
    ax.set_ylabel("Signal")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # Save figure
    output_path = FIGURES_DIR / f"stat_correlation_{subject_id:03d}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def process_modality(
    raw_data: np.ndarray,
    sfreq: int,
    modality: str,
    subject_id: int,
    verbose: bool = False,
) -> dict:
    """Process a single modality for statistical analysis.

    Args:
        raw_data: Raw signal data (n_channels, n_samples) or (n_samples,) for single channel.
        sfreq: Sampling frequency.
        modality: Modality name.
        subject_id: Subject ID.
        verbose: Enable verbose output.

    Returns:
        Dictionary with all statistical results.
    """
    results: dict = {
        "channels": {},
        "aggregate": {},
        "homoscedasticity": {},
    }

    # Handle different dimensionality
    if raw_data.ndim == 1:
        raw_data = raw_data.reshape(1, -1)
        ch_names = [CHANNELS.get(modality, ["CH"])[0]]
    else:
        ch_names = CHANNELS.get(modality, [f"CH{i}" for i in range(raw_data.shape[0])])

    # Per-channel analysis
    for ch_idx, ch_name in enumerate(ch_names):
        if ch_idx >= raw_data.shape[0]:
            break

        channel_data = raw_data[ch_idx]

        # Compute statistics
        desc_stats = compute_descriptive_stats(channel_data)
        quartiles = compute_quartiles(channel_data)
        normality = test_normality(channel_data)

        results["channels"][ch_name] = {
            "descriptive": desc_stats,
            "quartiles": quartiles,
            "normality": normality,
        }

        # Generate visualizations
        plot_histogram(channel_data, modality, ch_name, subject_id)
        plot_qq(channel_data, modality, ch_name, subject_id)

    # Generate boxplot for this modality
    data_per_channel = {
        ch_names[i]: raw_data[i] for i in range(min(len(ch_names), raw_data.shape[0]))
    }
    plot_boxplot(data_per_channel, modality, subject_id)

    # Aggregate statistics across channels
    if raw_data.shape[0] > 1:
        # Stack all channels
        all_channel_data = raw_data.reshape(
            raw_data.shape[0], -1
        ).T  # (n_samples, n_channels)
        # Flatten to 1D for aggregate stats
        aggregate_flat = all_channel_data.flatten()
        aggregate_flat = aggregate_flat[~np.isnan(aggregate_flat)]

        if len(aggregate_flat) >= 10:
            results["aggregate"] = {
                "descriptive": compute_descriptive_stats(aggregate_flat),
                "quartiles": compute_quartiles(aggregate_flat),
                "normality": test_normality(aggregate_flat),
            }

        # Homoscedasticity test across channels
        channel_groups = [
            raw_data[i][~np.isnan(raw_data[i])] for i in range(raw_data.shape[0])
        ]
        results["homoscedasticity"]["between_channels"] = test_homoscedasticity(
            channel_groups
        )

    if verbose:
        norm_count = sum(
            1 for ch in results["channels"].values() if ch["normality"].get("is_normal")
        )
        total_ch = len(results["channels"])
        print(
            f"      {modality.upper()}: {total_ch} channels, {norm_count}/{total_ch} normal"
        )

    return results


def _compile_summary_stats(all_subject_results: dict) -> tuple[str, str]:
    """Compile summary statistics across all subjects.

    Args:
        all_subject_results: Dictionary of subject results.

    Returns:
        Tuple of (normality_summary, homoscedasticity_summary) strings.
    """
    total_normal = 0
    total_tested = 0
    homoscedasticity_results = []

    for _subj_str, subj_data in all_subject_results.items():
        for _modality, mod_data in subj_data.items():
            for _ch_name, ch_results in mod_data.get("channels", {}).items():
                if ch_results["normality"].get("is_normal") is not None:
                    total_tested += 1
                    if ch_results["normality"]["is_normal"]:
                        total_normal += 1

            if "between_channels" in mod_data.get("homoscedasticity", {}):
                homoscedasticity_results.append(
                    mod_data["homoscedasticity"]["between_channels"]["is_homoscedastic"]
                )

    # Normality summary
    if total_tested > 0:
        normality_pct = (total_normal / total_tested) * 100
        normality_summary = f"{total_normal}/{total_tested} ({normality_pct:.1f}%) channels passed normality test"
    else:
        normality_summary = "No channels tested"

    # Homoscedasticity summary
    if homoscedasticity_results:
        homo_pct = (sum(homoscedasticity_results) / len(homoscedasticity_results)) * 100
        homoscedasticity_summary = (
            f"{sum(homoscedasticity_results)}/{len(homoscedasticity_results)} "
            f"({homo_pct:.1f}%) modality-channel groups showed homoscedasticity"
        )
    else:
        homoscedasticity_summary = "No homoscedasticity tests performed"

    return normality_summary, homoscedasticity_summary


def _generate_global_correlation(
    all_correlation_data: dict[int, dict[str, np.ndarray]],
) -> None:
    """Generate aggregate correlation heatmap across all subjects.

    Args:
        all_correlation_data: Dictionary mapping subject IDs to correlation data.
    """
    if len(all_correlation_data) <= 1:
        return

    global_corr_data: dict[str, list] = {}
    for _subj_id, corr_data in all_correlation_data.items():
        for key, values in corr_data.items():
            if key not in global_corr_data:
                global_corr_data[key] = []
            global_corr_data[key].extend(values.tolist()[:5000])  # Limit samples

    global_corr_np = {
        k: np.array(v) for k, v in global_corr_data.items() if len(v) > 100
    }
    if global_corr_np:
        plot_correlation_heatmap(global_corr_np, 999)  # 999 = aggregate


def run(subject_id: int | None = None, verbose: bool = False) -> None:  # noqa: C901
    """Execute Stage 3 statistical analysis pipeline.

    Args:
        subject_id: Optional specific subject to process. If None, process all.
        verbose: Enable verbose output.
    """
    # Ensure output directories exist
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list_subjects()

    if verbose:
        print("Stage 3: Statistical Analysis")
        print(f"Processing {len(subjects)} subjects: {subjects}")

    all_subject_results: dict = {}
    all_correlation_data: dict[int, dict[str, np.ndarray]] = {}

    for subj_id in subjects:
        if verbose:
            print(f"  Processing subject {subj_id:03d}...")

        try:
            data = load(subj_id)
        except FileNotFoundError as e:
            print(f"Warning: Could not load subject {subj_id}: {e}")
            continue

        subject_results: dict = {}
        correlation_data: dict[str, np.ndarray] = {}

        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality not in data:
                continue

            modality_data: ModalityDict = data[modality]
            raw = modality_data["data"]
            sfreq = SFREQ.get(modality, 250)

            # Get data as numpy array (n_channels, n_samples)
            raw_np = raw.get_data()

            # Process modality
            mod_results = process_modality(raw_np, sfreq, modality, subj_id, verbose)
            subject_results[modality] = mod_results

            # Collect data for correlation (downsample if needed)
            for ch_idx, ch_name in enumerate(CHANNELS.get(modality, ["CH"])):
                if ch_idx < raw_np.shape[0]:
                    # Downsample for memory efficiency
                    step = max(1, raw_np.shape[1] // 10000)
                    correlation_data[f"{modality}_{ch_name}"] = raw_np[ch_idx][::step]

        all_subject_results[str(subj_id)] = subject_results
        all_correlation_data[subj_id] = correlation_data

        # Generate correlation heatmap for this subject
        if correlation_data:
            plot_correlation_heatmap(correlation_data, subj_id)

        # Save per-subject statistics
        subject_metrics_path = METRICS_DIR / f"s{subj_id:03d}_statistics.json"
        with open(subject_metrics_path, "w") as f:
            json.dump(subject_results, f, indent=2)

    # Generate aggregate correlation heatmap across all subjects
    _generate_global_correlation(all_correlation_data)

    # Compile overall summary
    normality_summary, homoscedasticity_summary = _compile_summary_stats(
        all_subject_results
    )

    # Save aggregated metrics
    aggregate_metrics = {
        "subjects_analyzed": len(all_subject_results),
        "per_subject": all_subject_results,
        "interpretation": {
            "normality_summary": normality_summary,
            "homoscedasticity_summary": homoscedasticity_summary,
            "correlation_summary": f"Correlation heatmaps generated for {len(all_correlation_data)} subjects",
        },
    }

    metrics_path = METRICS_DIR / "statistics.json"
    with open(metrics_path, "w") as f:
        json.dump(aggregate_metrics, f, indent=2)

    if verbose:
        print(f"\nStage 3 complete!")
        print(f"  Subjects analyzed: {len(all_subject_results)}")
        print(f"  Normality: {normality_summary}")
        print(f"  Homoscedasticity: {homoscedasticity_summary}")
        print(f"  Metrics: {METRICS_DIR}")
        print(f"  Figures: {FIGURES_DIR}")
