"""Plot biosignals from the DriveDB dataset."""

import argparse
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from load_drivedb import DATA_DIR, load_record, list_records


def plot_signals(
    record_name: str,
    data_dir: str | None = None,
    signals: list[str] | None = None,
    duration_sec: float | None = None,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Plot all signals from a DriveDB record.

    Args:
        record_name: Name of the record (e.g., 'drive01')
        data_dir: Optional path to data directory
        signals: Optional list of signal names to plot (default: all)
        duration_sec: Optional duration in seconds to plot (default: all)
        show: Whether to display the plot
        save_path: Optional path to save the figure
    """
    # Load the record
    record = load_record(record_name, data_dir)

    # Get signal indices to plot
    if signals is None:
        sig_indices = list(range(len(record.sig_name)))
    else:
        sig_indices = [i for i, name in enumerate(record.sig_name) if name in signals]
        if not sig_indices:
            available = ", ".join(record.sig_name)
            raise ValueError(
                f"None of the requested signals found. Available: {available}"
            )

    # Calculate time axis
    n_samples = record.p_signal.shape[0]
    fs = record.fs

    # Limit to duration if specified
    if duration_sec is not None:
        max_samples = int(duration_sec * fs)
        n_samples = min(n_samples, max_samples)

    time_sec = np.arange(n_samples) / fs

    # Create subplots
    n_signals = len(sig_indices)
    fig, axes = plt.subplots(n_signals, 1, figsize=(14, 3 * n_signals), sharex=True)

    if n_signals == 1:
        axes = [axes]

    # Plot each signal
    for ax_idx, sig_idx in enumerate(sig_indices):
        ax = axes[ax_idx]
        signal_data = record.p_signal[:n_samples, sig_idx]
        sig_name = record.sig_name[sig_idx]
        sig_unit = record.units[sig_idx]

        ax.plot(time_sec, signal_data, linewidth=0.5, color="steelblue")
        ax.set_ylabel(f"{sig_name}\n({sig_unit})", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Add stats annotation
        mean_val = np.mean(signal_data)
        std_val = np.std(signal_data)
        ax.axhline(mean_val, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.text(
            0.02,
            0.95,
            f"μ={mean_val:.2f}, σ={std_val:.2f}",
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    axes[-1].set_xlabel("Time (seconds)", fontsize=12)
    fig.suptitle(
        f"DriveDB - {record_name}\nSampling: {fs} Hz | Duration: {n_samples / fs:.1f} s",
        fontsize=14,
    )

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")

    if show:
        plt.show()


def plot_signals_saturation_histogram(
    record_name: str,
    data_dir: str | None = None,
    signals: list[str] | None = None,
) -> None:
    """Plot histogram of signal values to check for saturation.

    Args:
        record_name: Name of the record (e.g., 'drive01')
        data_dir: Optional path to data directory
        signal_name: Name of the signal to analyze (default: 'ECG')
    """
    record = load_record(record_name, data_dir)

    # Find signal index
    if signals is None:
        sig_indices = list(range(len(record.sig_name)))
    else:
        sig_indices = [i for i, name in enumerate(record.sig_name) if name in signals]
        if not sig_indices:
            available = ", ".join(record.sig_name)
            raise ValueError(
                f"None of the requested signals found. Available: {available}"
            )

    fig, ax = plt.subplots(len(sig_indices), figsize=(8, 4))

    for i, sig_idx in enumerate(sig_indices):
        signal_data = record.p_signal[:, sig_idx]
        sig_name = record.sig_name[sig_idx]

        ax[i].hist(signal_data, bins=50, color="steelblue", alpha=0.7)
        ax[i].set_title(f"{sig_name} Value Distribution", fontsize=10)
        ax[i].set_xlabel("Signal Value", fontsize=9)
        ax[i].set_ylabel("Count", fontsize=9)
        ax[i].grid(True, alpha=0.3)

    plt.show()


def plot_signals_summary(records: list[str], data_dir: str | None = None) -> None:
    """Plot a summary view of multiple records (first 10 seconds each).

    Args:
        records: List of record names
        data_dir: Optional path to data directory
    """
    n_records = len(records)
    fig, axes = plt.subplots(n_records, 1, figsize=(14, 2 * n_records), sharex=True)

    if n_records == 1:
        axes = [axes]

    for ax_idx, record_name in enumerate(records):
        ax = axes[ax_idx]
        record = load_record(record_name, data_dir)

        # Plot first 10 seconds of ECG (usually index 0)
        n_samples = min(int(10 * record.fs), record.sig_len)
        time_sec = np.arange(n_samples) / record.fs
        ecg_signal = record.p_signal[:n_samples, 0]

        ax.plot(time_sec, ecg_signal, linewidth=0.5, color="steelblue")
        ax.set_ylabel(record.sig_name[0], fontsize=9)
        ax.set_title(record_name, fontsize=10, loc="left")
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Time (seconds)", fontsize=12)
    fig.suptitle("DriveDB - ECG Summary (First 10 seconds)", fontsize=14)

    plt.tight_layout()
    plt.show()


def plot_signals_psd(
    record_name: str,
    data_dir: str | None = None,
    signals: list[str] | None = None,
    duration_sec: float | None = None,
    nperseg: int = 2048,
    show: bool = True,
    save_path: str | None = None,
) -> None:
    """Plot Power Spectral Density (PSD) of signals from a DriveDB record.

    Uses Welch's method for PSD estimation.

    Args:
        record_name: Name of the record (e.g., 'drive01')
        data_dir: Optional path to data directory
        signals: Optional list of signal names to plot (default: all)
        duration_sec: Optional duration in seconds to analyze (default: all)
        nperseg: Length of each segment for Welch's method (default: 2048)
        show: Whether to display the plot
        save_path: Optional path to save the figure
    """
    # Load the record
    record = load_record(record_name, data_dir)

    # Get signal indices to plot
    if signals is None:
        sig_indices = list(range(len(record.sig_name)))
    else:
        sig_indices = [i for i, name in enumerate(record.sig_name) if name in signals]
        if not sig_indices:
            available = ", ".join(record.sig_name)
            raise ValueError(
                f"None of the requested signals found. Available: {available}"
            )

    # Calculate samples
    n_samples = record.p_signal.shape[0]
    fs = record.fs

    # Limit to duration if specified
    if duration_sec is not None:
        max_samples = int(duration_sec * fs)
        n_samples = min(n_samples, max_samples)

    # Create subplots
    n_signals = len(sig_indices)
    fig, axes = plt.subplots(n_signals, 1, figsize=(14, 3 * n_signals), sharex=True)

    if n_signals == 1:
        axes = [axes]

    # Compute and plot PSD for each signal
    for ax_idx, sig_idx in enumerate(sig_indices):
        ax = axes[ax_idx]
        signal_data = record.p_signal[:n_samples, sig_idx]
        sig_name = record.sig_name[sig_idx]
        sig_unit = record.units[sig_idx]

        # Compute PSD using Welch's method
        # nperseg adjusted to not exceed data length
        nperseg_actual = min(nperseg, n_samples)
        freqs, psd = signal.welch(
            signal_data, fs=fs, nperseg=nperseg_actual, noverlap=nperseg_actual // 2
        )

        # Plot PSD
        ax.semilogy(freqs, psd, linewidth=0.8, color="steelblue")
        ax.set_ylabel(f"{sig_name}\n(psd: {sig_unit}²/Hz)", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Find dominant frequency
        if len(psd) > 0:
            dom_freq_idx = np.argmax(psd)
            dom_freq = freqs[dom_freq_idx]
            ax.axvline(dom_freq, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
            ax.text(
                0.02,
                0.95,
                f"Dom. freq: {dom_freq:.2f} Hz",
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            )

        # Mark frequency bands for ECG-like signals
        if "ECG" in sig_name.upper() or "ECG" in sig_name:
            # Mark typical ECG frequency range (0.5-40 Hz)
            ax.axvspan(0.5, 40, alpha=0.1, color="green", label="ECG band")
            ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Frequency (Hz)", fontsize=12)
    fig.suptitle(
        f"DriveDB - {record_name} - Power Spectral Density\n"
        f"Sampling: {fs} Hz | Duration: {n_samples / fs:.1f} s | nperseg: {nperseg_actual}",
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
    parser = argparse.ArgumentParser(description="Plot DriveDB biosignals")
    parser.add_argument(
        "record", nargs="?", default="drive01", help="Record name (default: drive01)"
    )
    parser.add_argument(
        "--data-dir", type=str, default=None, help="Data directory path"
    )
    parser.add_argument(
        "--signals", type=str, nargs="+", default=None, help="Signal names to plot"
    )
    parser.add_argument(
        "--duration", type=float, default=None, help="Duration in seconds to plot"
    )
    parser.add_argument("--save", type=str, default=None, help="Save figure to path")
    parser.add_argument("--no-show", action="store_true", help="Don't display the plot")
    parser.add_argument(
        "--summary", action="store_true", help="Show summary of all records"
    )
    parser.add_argument(
        "--psd",
        action="store_true",
        help="Plot Power Spectral Density instead of time domain",
    )
    parser.add_argument(
        "--nperseg",
        type=int,
        default=2048,
        help="Segment length for PSD (default: 2048)",
    )

    args = parser.parse_args()

    if args.summary:
        records = list_records(args.data_dir)
        print(f"Showing summary of {len(records)} records...")
        plot_signals_summary(records, args.data_dir)
    elif args.psd:
        plot_signals_psd(
            record_name=args.record,
            data_dir=args.data_dir,
            signals=args.signals,
            duration_sec=args.duration,
            nperseg=args.nperseg,
            show=not args.no_show,
            save_path=args.save,
        )
    else:
        plot_signals(
            record_name=args.record,
            data_dir=args.data_dir,
            signals=args.signals,
            duration_sec=args.duration,
            show=not args.no_show,
            save_path=args.save,
        )

    plot_signals_saturation_histogram(args.record, args.data_dir)


if __name__ == "__main__":
    main()
