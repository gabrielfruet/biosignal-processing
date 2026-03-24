"""Stage 1: Biosignal Acquisition.

Validates acquisition parameters, detects problems, and generates visualizations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict, cast

import matplotlib.pyplot as plt
import numpy as np

from biosignal.config import (
    OUTPUT_DIR,
    METRICS_DIR,
    FIGURES_DIR,
    DATA_OUT_DIR,
    SFREQ,
    CHANNELS,
    NYQUIST_MAX_FREQ,
)
from biosignal.io.ieee import load, list_subjects, SubjectDict, ModalityDict


class LoadedSubjectData(TypedDict):
    """Typed dict for loaded subject data."""

    eeg: ModalityDict
    ecg: ModalityDict
    emg: ModalityDict
    fnirs: ModalityDict


def validate_nyquist(sfreq: int, modality: str) -> dict[str, Any]:
    """Validate sampling rate follows Nyquist theorem.

    Args:
        sfreq: Sampling frequency in Hz.
        modality: Modality name (e.g., 'eeg', 'ecg').

    Returns:
        Dictionary with validation results.
    """
    max_freq = NYQUIST_MAX_FREQ.get(modality, 50)
    ratio = sfreq / (2 * max_freq)
    return {
        "sfreq": sfreq,
        "max_freq": max_freq,
        "ratio": ratio,
        "compliant": sfreq >= 2 * max_freq,
    }


def identify_problems(raw: Any) -> dict[str, list[str]]:
    """Detect signal quality problems.

    Args:
        raw: MNE Raw object.

    Returns:
        Dictionary of problem types to affected channels.
    """
    data = raw.get_data()
    ch_names = raw.ch_names
    sfreq = raw.info["sfreq"]

    problems: dict[str, list[str]] = {
        "flat_channels": [],
        "clipping_channels": [],
        "dead_channels": [],
        "noisy_channels": [],
    }

    # Calculate variance for all channels
    variances = np.var(data, axis=1)
    median_var = np.median(variances)

    for i, ch_name in enumerate(ch_names):
        ch_data = data[i]

        # Flat line: std dev < 1e-6
        if np.std(ch_data) < 1e-6:
            problems["flat_channels"].append(ch_name)

        # Clipping: >5% samples at min or max
        min_val, max_val = ch_data.min(), ch_data.max()
        range_val = max_val - min_val
        if range_val > 0:
            clip_threshold_low = min_val + 0.001 * range_val
            clip_threshold_high = max_val - 0.001 * range_val
            clipped = np.sum(
                (ch_data <= clip_threshold_low) | (ch_data >= clip_threshold_high)
            )
            if clipped / len(ch_data) > 0.05:
                problems["clipping_channels"].append(ch_name)

        # Dead channel: all values identical
        if np.all(ch_data == ch_data[0]):
            problems["dead_channels"].append(ch_name)

        # Excessive noise: variance > 3x median
        if variances[i] > 3 * median_var:
            problems["noisy_channels"].append(ch_name)

    return problems


def document_protocol() -> dict[str, Any]:
    """Document experimental protocol.

    Returns:
        Protocol metadata dictionary.
    """
    return {
        "dataset": "IEEE Multimodal Emotion Recognition",
        "subjects": 16,
        "subject_ids": list_subjects(),
        "task_type": "emotion_induction",
        "baseline_duration_s": 30,
        "stimulation_duration_s": 30,
        "total_duration_s": 60,
        "intervals": ["baseline", "stimulation", "recovery"],
    }


def document_hardware() -> dict[str, Any]:
    """Document hardware specifications.

    Returns:
        Hardware specs per modality.
    """
    return {
        "eeg": {
            "channels": 8,
            "sfreq_hz": SFREQ["eeg"],
            "channel_names": CHANNELS["eeg"],
            "system": "Emotiv EPOC+",
        },
        "ecg": {
            "channels": 1,
            "sfreq_hz": SFREQ["ecg"],
        },
        "emg": {
            "channels": 1,
            "sfreq_hz": SFREQ["emg"],
        },
        "fnirs": {
            "channels": 2,
            "measures": ["HbO", "HbR"],
            "sfreq_hz": SFREQ["fnirs"],
            "transformation": "Beer-Lambert Law",
        },
    }


def plot_raw_signals(
    data: dict[str, Any],
    subject_id: int,
    problems: dict[str, Any],
) -> None:
    """Generate multi-panel raw signal visualization.

    Args:
        data: Loaded subject data.
        subject_id: Subject ID.
        problems: Detected problems per modality.
    """
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(4, 1, hspace=0.4, left=0.1, right=0.95, top=0.93, bottom=0.06)
    fig.suptitle(
        f"Subject {subject_id:03d} - Raw Biosignals", fontsize=14, fontweight="bold"
    )

    # Color scheme
    cmap = plt.get_cmap("tab10")
    colors = [cmap(i) for i in range(10)]

    # EEG: 5 seconds, all 8 channels stacked vertically
    ax_eeg = fig.add_subplot(gs[0])
    if "eeg" in data:
        eeg = data["eeg"]["data"]
        eeg_data = eeg.get_data()
        eeg_sfreq = eeg.info["sfreq"]
        duration = 5
        n_samples = int(duration * eeg_sfreq)
        time = np.arange(n_samples) / eeg_sfreq

        # Calculate offset for each channel
        offset_step = np.max(np.std(eeg_data[:, :n_samples], axis=1)) * 3
        for i, ch_name in enumerate(eeg.ch_names):
            ch_data = eeg_data[i, :n_samples] * 1e6
            label = ch_name.replace("EEG_", "")
            ax_eeg.plot(
                time,
                ch_data + i * offset_step,
                linewidth=0.4,
                color=colors[i % 10],
                label=label,
            )

        ax_eeg.set_ylabel("EEG (μV)")
        ax_eeg.set_title(f"EEG - 8 Channels ({duration}s window) | {eeg_sfreq} Hz")
        ax_eeg.legend(loc="upper right", ncol=4, fontsize=7)
        ax_eeg.grid(True, alpha=0.3, linestyle="--")
        ax_eeg.set_xlim(time[0], time[-1])
    else:
        ax_eeg.text(
            0.5,
            0.5,
            "EEG: Not available",
            ha="center",
            va="center",
            transform=ax_eeg.transAxes,
        )

    # ECG: 10 seconds
    ax_ecg = fig.add_subplot(gs[1])
    if "ecg" in data:
        ecg = data["ecg"]["data"]
        ecg_data = ecg.get_data()
        ecg_sfreq = ecg.info["sfreq"]
        duration = 10
        n_samples = int(duration * ecg_sfreq)
        time = np.arange(n_samples) / ecg_sfreq
        ax_ecg.plot(time, ecg_data[0, :n_samples] * 1e3, linewidth=0.5, color=colors[1])
        ax_ecg.set_ylabel("ECG (mV)")
        ax_ecg.set_title(f"ECG ({duration}s window) | {ecg_sfreq} Hz")
        ax_ecg.grid(True, alpha=0.3, linestyle="--")
        ax_ecg.set_xlim(time[0], time[-1])
    else:
        ax_ecg.text(
            0.5,
            0.5,
            "ECG: Not available",
            ha="center",
            va="center",
            transform=ax_ecg.transAxes,
        )

    # EMG: 5 seconds
    ax_emg = fig.add_subplot(gs[2])
    if "emg" in data:
        emg = data["emg"]["data"]
        emg_data = emg.get_data()
        emg_sfreq = emg.info["sfreq"]
        duration = 5
        n_samples = int(duration * emg_sfreq)
        time = np.arange(n_samples) / emg_sfreq
        ax_emg.plot(time, emg_data[0, :n_samples] * 1e3, linewidth=0.5, color=colors[2])
        ax_emg.set_ylabel("EMG (mV)")
        ax_emg.set_title(f"EMG ({duration}s window) | {emg_sfreq} Hz")
        ax_emg.grid(True, alpha=0.3, linestyle="--")
        ax_emg.set_xlim(time[0], time[-1])
    else:
        ax_emg.text(
            0.5,
            0.5,
            "EMG: Not available",
            ha="center",
            va="center",
            transform=ax_emg.transAxes,
        )

    # fNIRS: 30 seconds, HbO and HbR
    ax_fnirs = fig.add_subplot(gs[3])
    if "fnirs" in data:
        fnirs = data["fnirs"]["data"]
        fnirs_data = fnirs.get_data()
        fnirs_sfreq = fnirs.info["sfreq"]
        duration = 30
        n_samples = int(duration * fnirs_sfreq)
        n_plot = min(n_samples, fnirs_data.shape[1])
        time = np.arange(n_plot) / fnirs_sfreq
        ax_fnirs.plot(
            time,
            fnirs_data[0, :n_plot] * 1e3,
            label="HbO",
            linewidth=0.8,
            color="tab:red",
        )
        ax_fnirs.plot(
            time,
            fnirs_data[1, :n_plot] * 1e3,
            label="HbR",
            linewidth=0.8,
            color="tab:blue",
        )
        ax_fnirs.set_ylabel("Conc. (mM·mm)")
        ax_fnirs.set_xlabel("Time (s)")
        ax_fnirs.set_title(f"fNIRS - HbO/HbR ({duration}s window) | {fnirs_sfreq} Hz")
        ax_fnirs.legend(loc="upper right")
        ax_fnirs.grid(True, alpha=0.3, linestyle="--")
        ax_fnirs.set_xlim(time[0], time[-1])
    else:
        ax_fnirs.text(
            0.5,
            0.5,
            "fNIRS: Not available",
            ha="center",
            va="center",
            transform=ax_fnirs.transAxes,
        )
        ax_fnirs.set_xlabel("Time (s)")

    output_path = FIGURES_DIR / f"s{subject_id:03d}_raw_signals.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_overview(
    all_data: dict[int, dict[str, Any]], subject_problems: dict[int, dict[str, Any]]
) -> None:
    """Generate 4x4 grid overview of all subjects.

    Args:
        all_data: Dictionary of subject_id -> loaded data.
        subject_problems: Dictionary of subject_id -> problems dict.
    """
    fig, axes = plt.subplots(4, 4, figsize=(14, 10), constrained_layout=True)
    fig.suptitle(
        "EEG Overview - AF7 Channel (3s window)", fontsize=14, fontweight="bold"
    )

    cmap = plt.get_cmap("tab10")
    colors = [cmap(i) for i in range(10)]

    for idx, subject_id in enumerate(sorted(all_data.keys())):
        row = idx // 4
        col = idx % 4
        ax = axes[row, col]

        data = all_data[subject_id]
        if "eeg" in data:
            eeg = data["eeg"]["data"]
            eeg_data = eeg.get_data()
            eeg_sfreq = eeg.info["sfreq"]
            duration = 3
            n_samples = int(duration * eeg_sfreq)

            # Find AF7 channel (first EEG channel)
            ch_idx = 0
            for i, ch_name in enumerate(eeg.ch_names):
                if "AF7" in ch_name:
                    ch_idx = i
                    break

            time = np.arange(n_samples) / eeg_sfreq
            ax.plot(
                time, eeg_data[ch_idx, :n_samples] * 1e6, linewidth=0.5, color=colors[0]
            )

            # Red border for problematic subjects
            problems = subject_problems.get(subject_id, {})
            eeg_problems = problems.get("eeg", {}).get("problems", {})
            has_problems = (
                eeg_problems.get("flat_channels")
                or eeg_problems.get("dead_channels")
                or eeg_problems.get("noisy_channels")
            )
            if has_problems:
                for spine in ax.spines.values():
                    spine.set_edgecolor("red")
                    spine.set_linewidth(2)
        else:
            ax.text(0.5, 0.5, "No EEG", ha="center", va="center")

        ax.set_title(f"Subject {subject_id:03d}", fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3, linestyle="--")

    # Add x/y labels on edge subplots only
    for ax in axes[-1, :]:
        ax.set_xlabel("Time (s)", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("μV", fontsize=8)

    output_path = FIGURES_DIR / "overview_all_subjects.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def run(subject_id: int | None = None, verbose: bool = False) -> None:  # noqa: C901
    """Execute Stage 1 acquisition pipeline.

    Args:
        subject_id: Optional specific subject to process. If None, process all.
        verbose: Enable verbose output.
    """
    # Ensure output directories exist
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_OUT_DIR.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list_subjects()

    if verbose:
        print(f"Stage 1: Biosignal Acquisition")
        print(f"Processing {len(subjects)} subjects: {subjects}")

    # Document protocol and hardware
    protocol = document_protocol()
    hardware = document_hardware()

    # Validate Nyquist for all modalities
    nyquist_validation = {}
    for modality, sfreq in SFREQ.items():
        nyquist_validation[modality] = validate_nyquist(sfreq, modality)

    # Collect all data and problems
    all_data: dict[int, SubjectDict] = {}
    subject_problems: dict[int, dict[str, Any]] = {}

    # Process each subject
    for subj_id in subjects:
        if verbose:
            print(f"  Processing subject {subj_id:03d}...")

        try:
            data = load(subj_id)
            all_data[subj_id] = data
        except FileNotFoundError as e:
            print(f"Warning: Could not load subject {subj_id}: {e}")
            continue

        # Detect problems for each modality
        problems: dict[str, Any] = {}
        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality in data:
                raw = cast(Any, data[modality]["data"])
                problems[modality] = {
                    "channels": len(raw.ch_names),
                    "samples": raw.get_data().shape[1],
                    "duration_s": raw.get_data().shape[1] / raw.info["sfreq"],
                    "problems": identify_problems(raw),
                }
            else:
                problems[modality] = {"problems": {}}

        subject_problems[subj_id] = problems

        # Save per-subject metrics
        metrics = {
            "subject_id": subj_id,
            "modalities": problems,
        }
        metrics_path = METRICS_DIR / f"s{subj_id:03d}_acquisition.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        # Generate individual subject plot
        plot_raw_signals(data, subj_id, problems)

    # Generate overview plot
    plot_overview(all_data, subject_problems)

    # Save acquisition metadata
    metadata = {
        "dataset": protocol["dataset"],
        "protocol": protocol,
        "hardware": hardware,
        "nyquist_validation": nyquist_validation,
    }
    metadata_path = DATA_OUT_DIR / "acquisition_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Save summary metrics
    total_subjects = len(all_data)
    subjects_with_problems = sum(
        1
        for p in subject_problems.values()
        if any(
            m.get("problems", {}).get(k)
            for m in p.values()
            for k in [
                "flat_channels",
                "clipping_channels",
                "dead_channels",
                "noisy_channels",
            ]
        )
    )

    problem_summary: dict[str, int] = {
        "flat_channels": 0,
        "clipping_channels": 0,
        "dead_channels": 0,
        "noisy_channels": 0,
    }
    for p in subject_problems.values():
        for m in p.values():
            probs = m.get("problems", {})
            for k in problem_summary:
                problem_summary[k] += len(probs.get(k, []))

    summary = {
        "total_subjects": total_subjects,
        "subjects_with_problems": subjects_with_problems,
        "problem_summary": problem_summary,
    }
    summary_path = METRICS_DIR / "acquisition_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print(f"\nStage 1 complete!")
        print(f"  Metrics: {METRICS_DIR}")
        print(f"  Figures: {FIGURES_DIR}")
        print(f"  Metadata: {metadata_path}")
