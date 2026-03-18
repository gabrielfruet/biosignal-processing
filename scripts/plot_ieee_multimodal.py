"""Plot biosignals from the IEEE Multimodal dataset."""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

from load_ieee_multimodal import load, list_subjects, SFREQ, CHANNELS


def plot_signals(
    subject_id: int,
    modalities: list[str] | None = None,
    window_sec: float | None = None,
    markers_to_show: list[str] | None = None,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Plot all biosignals for a subject.

    Args:
        subject_id: Subject ID (0-15)
        modalities: List of modalities to plot (default: all)
        window_sec: Optional time window around markers to plot (seconds)
        markers_to_show: Which markers to show ('baseline', 'stim_start', 'stim_end')
        show: Whether to display the plot
        save_path: Optional path to save the figure
    """
    available_modalities = ["eeg", "ecg", "emg", "fnirs"]

    if modalities is None:
        modalities = available_modalities
    else:
        for mod in modalities:
            if mod not in available_modalities:
                raise ValueError(
                    f"Unknown modality: {mod}. Available: {available_modalities}"
                )

    # Load data
    data = load(subject_id, modalities=modalities)
    markers = data["markers"]

    # Determine time window
    if window_sec is not None:
        markers_to_show = markers_to_show or ["stim_start"]
        # Get reference index from first marker
        ref_marker = markers_to_show[0]
        ref_modality = (
            "EEG" if "eeg" in modalities else list(markers[ref_marker].keys())[0]
        )
        ref_idx = markers[ref_marker][ref_modality]
        ref_sfreq = SFREQ.get(
            ref_modality.lower()
            .replace("eeg", "eeg")
            .replace("fnirs", "fnirs")
            .replace("emg_ecg", "ecg"),
            512,
        )

        start_idx = max(0, int(ref_idx - window_sec * ref_sfreq))
        end_idx = int(ref_idx + window_sec * ref_sfreq)
    else:
        start_idx = 0
        end_idx = None

    # Create subplots
    n_modalities = len(modalities)
    fig, axes = plt.subplots(
        n_modalities, 1, figsize=(14, 3 * n_modalities), sharex=True
    )

    if n_modalities == 1:
        axes = [axes]

    for ax_idx, modality in enumerate(modalities):
        ax = axes[ax_idx]
        raw = data[modality]["data"]
        sfreq = data[modality]["sfreq"]
        ch_names = data[modality]["ch_names"]

        # Get data
        data_arr = raw.get_data()

        # Apply time window
        if end_idx is not None:
            # Adjust for different sampling rates
            ratio = sfreq / 512  # normalize to EEG rate
            start_adj = int(start_idx * ratio) if ratio != 1 else start_idx
            end_adj = int(end_idx * ratio) if ratio != 1 else end_idx

            # Ensure bounds
            n_samples = data_arr.shape[1]
            start_adj = min(start_adj, n_samples)
            end_adj = min(end_adj, n_samples)
            data_arr = data_arr[:, start_adj:end_adj]
        else:
            end_idx = data_arr.shape[1]

        time_sec = np.arange(data_arr.shape[1]) / sfreq

        # Plot each channel
        for ch_idx, ch_name in enumerate(ch_names):
            if ch_idx == 0:
                label = ch_name
            else:
                label = None
            ax.plot(time_sec, data_arr[ch_idx], linewidth=0.5, label=label)

        ax.set_ylabel(f"{modality.upper()}\n({sfreq} Hz)", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Add stats
        mean_val = np.mean(data_arr)
        std_val = np.std(data_arr)
        ax.axhline(mean_val, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.text(
            0.02,
            0.95,
            f"μ={mean_val:.4f}, σ={std_val:.4f}",
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

        # Plot markers
        if markers_to_show:
            for marker_name in markers_to_show:
                if marker_name in markers:
                    # Get marker for this modality
                    mod_key = modality.upper() if modality != "fnirs" else "Fnirs"
                    if "EMG" in mod_key or "ECG" in mod_key:
                        mod_key = "EMG_ECG"

                    if mod_key in markers[marker_name]:
                        marker_idx = markers[marker_name][mod_key]
                        # Adjust for sampling rate
                        if sfreq != 512:
                            marker_adj = marker_idx * (sfreq / 512)
                        else:
                            marker_adj = marker_idx
                        marker_time = marker_adj / sfreq

                        # Only plot if within window
                        if (
                            window_sec is None
                            or abs(marker_time - time_sec[len(time_sec) // 2])
                            < window_sec
                        ):
                            ax.axvline(
                                marker_time,
                                color="green",
                                linestyle="--",
                                linewidth=1.5,
                                alpha=0.8,
                            )

        if ch_names:
            ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Time (seconds)", fontsize=12)

    n_samples_total = end_idx - start_idx if end_idx else 0
    avg_sfreq = sum(SFREQ[m] for m in modalities) / len(modalities)
    fig.suptitle(
        f"IEEE Multimodal - Subject {subject_id}\n"
        f"Modalities: {modalities} | Duration: {n_samples_total / avg_sfreq:.1f} s",
        fontsize=14,
    )

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")

    if show:
        plt.show()


def plot_signals_psd(
    subject_id: int,
    modalities: list[str] | None = None,
    window_sec: float | None = None,
    nperseg: int = 1024,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Plot Power Spectral Density (PSD) of biosignals.

    Args:
        subject_id: Subject ID (0-15)
        modalities: List of modalities to plot (default: all)
        window_sec: Optional time window around stimulus to analyze
        nperseg: Length of each segment for Welch's method
        show: Whether to display the plot
        save_path: Optional path to save the figure
    """
    available_modalities = ["eeg", "ecg", "emg", "fnirs"]

    if modalities is None:
        modalities = available_modalities
    else:
        for mod in modalities:
            if mod not in available_modalities:
                raise ValueError(
                    f"Unknown modality: {mod}. Available: {available_modalities}"
                )

    # Load data
    data = load(subject_id, modalities=modalities)

    # Determine time window around stimulus start
    if window_sec is not None:
        markers = data["markers"]
        ref_idx = markers["stim_start"]["EEG"]
        start_idx = max(0, int(ref_idx - window_sec * 512))
        end_idx = int(ref_idx + window_sec * 512)
    else:
        start_idx = 0
        end_idx = None

    # Create subplots
    n_modalities = len(modalities)
    fig, axes = plt.subplots(
        n_modalities, 1, figsize=(14, 3 * n_modalities), sharex=True
    )

    if n_modalities == 1:
        axes = [axes]

    for ax_idx, modality in enumerate(modalities):
        ax = axes[ax_idx]
        raw = data[modality]["data"]
        sfreq = data[modality]["sfreq"]
        ch_names = data[modality]["ch_names"]

        # Get data
        data_arr = raw.get_data()

        # Apply time window (normalize to EEG rate)
        if end_idx is not None:
            ratio = sfreq / 512
            start_adj = int(start_idx * ratio)
            end_adj = int(end_idx * ratio)
            n_samples = data_arr.shape[1]
            start_adj = min(start_adj, n_samples)
            end_adj = min(end_adj, n_samples)
            data_arr = data_arr[:, start_adj:end_adj]

        # Compute PSD for each channel
        nperseg_actual = min(nperseg, data_arr.shape[1])

        for ch_idx, ch_name in enumerate(ch_names):
            freqs, psd = signal.welch(
                data_arr[ch_idx],
                fs=sfreq,
                nperseg=nperseg_actual,
                noverlap=nperseg_actual // 2,
            )

            if ch_idx == 0:
                label = ch_name
            else:
                label = ch_name

            ax.semilogy(freqs, psd, linewidth=0.8, label=label)

            # Find dominant frequency
            if len(psd) > 0:
                dom_freq_idx = np.argmax(psd)
                dom_freq = freqs[dom_freq_idx]

        ax.set_ylabel(f"{modality.upper()}\n(psd)", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Mark frequency bands
        if modality == "eeg":
            # Typical EEG bands
            bands = {
                "δ": (0.5, 4),
                "θ": (4, 8),
                "α": (8, 13),
                "β": (13, 30),
                "γ": (30, 40),
            }
            for band_name, (low, high) in bands.items():
                ax.axvspan(low, high, alpha=0.05, color="green")
                ax.text(
                    (low + high) / 2,
                    ax.get_ylim()[1] * 0.9,
                    band_name,
                    ha="center",
                    fontsize=8,
                    alpha=0.5,
                )
        elif modality == "ecg":
            ax.axvspan(0.5, 40, alpha=0.1, color="red", label="ECG band")
        elif modality == "emg":
            ax.axvspan(1, 20, alpha=0.1, color="orange", label="EMG band")

        ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Frequency (Hz)", fontsize=12)

    fig.suptitle(
        f"IEEE Multimodal - Subject {subject_id} - Power Spectral Density\n"
        f"Modalities: {modalities} | nperseg: {nperseg_actual}",
        fontsize=14,
    )

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")

    if show:
        plt.show()


def plot_signals_summary(
    subjects: list[int] | None = None,
    modality: str = "eeg",
    duration_sec: float = 10.0,
) -> None:
    """Plot summary of all subjects for a single modality.

    Args:
        subjects: List of subject IDs (default: all available)
        modality: Modality to plot ('eeg', 'ecg', 'emg', 'fnirs')
        duration_sec: Duration to plot in seconds
    """
    if subjects is None:
        subjects = list_subjects()

    n_subjects = len(subjects)
    fig, axes = plt.subplots(n_subjects, 1, figsize=(14, 2 * n_subjects), sharex=True)

    if n_subjects == 1:
        axes = [axes]

    sfreq = SFREQ[modality]
    n_samples = int(duration_sec * sfreq)

    for ax_idx, subject_id in enumerate(subjects):
        ax = axes[ax_idx]

        try:
            data = load(subject_id, modalities=[modality])
            raw = data[modality]["data"]
            ch_names = data[modality]["ch_names"]

            # Get first channel
            data_arr = raw.get_data()[0, :n_samples]
            time_sec = np.arange(n_samples) / sfreq

            ax.plot(time_sec, data_arr, linewidth=0.5, color="steelblue")
            ax.set_ylabel(ch_names[0] if ch_names else modality.upper(), fontsize=9)
            ax.set_title(f"Subject {subject_id}", fontsize=10, loc="left")
            ax.grid(True, alpha=0.3)

        except Exception as e:
            ax.text(0.5, 0.5, f"Error: {e}", transform=ax.transAxes, ha="center")
            ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (seconds)", fontsize=12)
    fig.suptitle(
        f"IEEE Multimodal - {modality.upper()} Summary (First {duration_sec} seconds)",
        fontsize=14,
    )

    plt.tight_layout()
    plt.show()


def plot_signals_histogram(
    subject_id: int,
    modalities: list[str] | None = None,
    bins: int = 50,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Plot histogram of signal values to check distribution and saturation.

    Args:
        subject_id: Subject ID (0-15)
        modalities: List of modalities to plot (default: all)
        bins: Number of bins for histogram (default: 50)
        show: Whether to display the plot
        save_path: Optional path to save the figure
    """
    available_modalities = ["eeg", "ecg", "emg", "fnirs"]

    if modalities is None:
        modalities = available_modalities
    else:
        for mod in modalities:
            if mod not in available_modalities:
                raise ValueError(
                    f"Unknown modality: {mod}. Available: {available_modalities}"
                )

    # Load data
    data = load(subject_id, modalities=modalities)

    # Create subplots - one per modality (channels aggregated)
    n_modalities = len(modalities)
    fig, axes = plt.subplots(n_modalities, 1, figsize=(12, 3 * n_modalities))

    if n_modalities == 1:
        axes = [axes]

    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    for ax_idx, modality in enumerate(modalities):
        ax = axes[ax_idx]

        if modality not in data:
            continue

        raw = data[modality]["data"]
        ch_names = data[modality]["ch_names"]
        data_arr = raw.get_data()

        # Plot histogram for each channel on the same axes
        for ch_idx, ch_name in enumerate(ch_names):
            signal_data = data_arr[ch_idx]
            color = colors[ch_idx % len(colors)]

            # Plot histogram with transparency
            ax.hist(
                signal_data,
                bins=bins,
                alpha=0.5,
                label=ch_name,
                color=color,
                edgecolor=color,
                linewidth=0.3,
            )

            # Add mean line
            mean_val = np.mean(signal_data)
            ax.axvline(mean_val, color=color, linestyle="--", linewidth=1.5, alpha=0.8)

        # Add statistics
        overall_mean = np.mean(data_arr)
        overall_std = np.std(data_arr)
        min_val = np.min(data_arr)
        max_val = np.max(data_arr)

        ax.set_title(
            f"{modality.upper()} - Signal Distribution ({len(ch_names)} channels)",
            fontsize=11,
        )
        ax.set_xlabel("Signal Value", fontsize=9)
        ax.set_ylabel("Count", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8, ncol=2)

        # Add stats text box
        stats_text = (
            f"Overall μ: {overall_mean:.4f}\nOverall σ: {overall_std:.4f}\n"
            f"Min: {min_val:.4f}\nMax: {max_val:.4f}"
        )
        ax.text(
            0.02,
            0.95,
            stats_text,
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    fig.suptitle(
        f"IEEE Multimodal - Subject {subject_id} - Signal Distribution",
        fontsize=14,
    )

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")

    if show:
        plt.show()


def plot_stimulus_response(
    subject_id: int,
    modality: str = "eeg",
    window_sec: float = 30.0,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Plot signals around stimulus onset.

    Args:
        subject_id: Subject ID (0-15)
        modality: Modality to plot ('eeg', 'ecg', 'emg', 'fnirs')
        window_sec: Time window before and after stimulus (seconds)
        show: Whether to display the plot
        save_path: Optional path to save the figure
    """
    # Load data
    data = load(subject_id, modalities=[modality])
    markers = data["markers"]
    raw = data[modality]["data"]
    sfreq = data[modality]["sfreq"]
    ch_names = data[modality]["ch_names"]

    # Get stimulus index
    if modality == "eeg":
        stim_idx = markers["stim_start"]["EEG"]
    elif modality == "fnirs":
        stim_idx = markers["stim_start"]["Fnirs"]
    else:
        stim_idx = markers["stim_start"]["EMG_ECG"]

    # Adjust for sampling rate
    ratio = sfreq / 512
    stim_idx_adj = int(stim_idx * ratio)

    # Calculate window
    window_samples = int(window_sec * sfreq)
    start_idx = max(0, stim_idx_adj - window_samples)
    end_idx = min(raw.get_data().shape[1], stim_idx_adj + window_samples)

    # Extract data
    data_arr = raw.get_data()[:, start_idx:end_idx]
    time_sec = (np.arange(data_arr.shape[1]) - (stim_idx_adj - start_idx)) / sfreq

    # Plot
    n_channels = len(ch_names)
    fig, axes = plt.subplots(n_channels, 1, figsize=(14, 3 * n_channels), sharex=True)

    if n_channels == 1:
        axes = [axes]

    for ch_idx, ch_name in enumerate(ch_names):
        ax = axes[ch_idx]
        ax.plot(time_sec, data_arr[ch_idx], linewidth=0.5, color="steelblue")
        ax.axvline(
            0, color="red", linestyle="--", linewidth=1.5, label="Stimulus onset"
        )
        ax.set_ylabel(ch_name, fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)

        # Shade baseline and stimulation periods
        ax.axvspan(-window_sec, 0, alpha=0.1, color="blue", label="Baseline")
        ax.axvspan(0, window_sec, alpha=0.1, color="green", label="Stimulus")

    axes[-1].set_xlabel("Time (seconds)", fontsize=12)
    fig.suptitle(
        f"IEEE Multimodal - Subject {subject_id} - {modality.upper()} Response\n"
        f"Window: ±{window_sec} s around stimulus",
        fontsize=14,
    )

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")

    if show:
        plt.show()


def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(description="Plot IEEE Multimodal biosignals")
    parser.add_argument(
        "subject",
        type=int,
        nargs="?",
        default=0,
        help="Subject ID (default: 0)",
    )
    parser.add_argument(
        "--modalities",
        "-m",
        type=str,
        nargs="+",
        default=None,
        help="Modalities to plot (eeg, ecg, emg, fnirs)",
    )
    parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=None,
        help="Duration in seconds to plot",
    )
    parser.add_argument(
        "--window",
        "-w",
        type=float,
        default=None,
        help="Time window around stimulus (seconds)",
    )
    parser.add_argument(
        "--markers",
        type=str,
        nargs="+",
        default=None,
        help="Markers to show (baseline, stim_start, stim_end)",
    )
    parser.add_argument("--save", type=str, default=None, help="Save figure to path")
    parser.add_argument("--no-show", action="store_true", help="Don't display the plot")
    parser.add_argument(
        "--summary", action="store_true", help="Show summary of all subjects"
    )
    parser.add_argument(
        "--modality-summary",
        type=str,
        default="eeg",
        help="Modality for summary (default: eeg)",
    )
    parser.add_argument(
        "--psd",
        action="store_true",
        help="Plot Power Spectral Density instead of time domain",
    )
    parser.add_argument(
        "--nperseg",
        type=int,
        default=1024,
        help="Segment length for PSD (default: 1024)",
    )
    parser.add_argument(
        "--response",
        "-r",
        action="store_true",
        help="Plot stimulus response (window around stimulus onset)",
    )
    parser.add_argument(
        "--histogram",
        action="store_true",
        help="Plot signal histogram/distribution instead of time domain",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=50,
        help="Number of bins for histogram (default: 50)",
    )

    args = parser.parse_args()

    show = not args.no_show

    if args.summary:
        plot_signals_summary(modality=args.modality_summary)
    elif args.histogram:
        plot_signals_histogram(
            subject_id=args.subject,
            modalities=args.modalities,
            bins=args.bins,
            show=show,
            save_path=args.save,
        )
    elif args.response:
        plot_stimulus_response(
            subject_id=args.subject,
            modality=args.modalities[0] if args.modalities else "eeg",
            window_sec=args.window or 30.0,
            show=show,
            save_path=args.save,
        )
    elif args.psd:
        plot_signals_psd(
            subject_id=args.subject,
            modalities=args.modalities,
            window_sec=args.duration,
            nperseg=args.nperseg,
            show=show,
            save_path=args.save,
        )
    else:
        plot_signals(
            subject_id=args.subject,
            modalities=args.modalities,
            window_sec=args.window,
            markers_to_show=args.markers,
            show=show,
            save_path=args.save,
        )


if __name__ == "__main__":
    main()
