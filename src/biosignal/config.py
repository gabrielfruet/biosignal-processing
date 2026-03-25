"""Centralized configuration constants for biosignal processing."""

from pathlib import Path

# Directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ieee-multimodal-extracted"
OUTPUT_DIR = PROJECT_ROOT / "output"
METRICS_DIR = OUTPUT_DIR / "metrics"
FIGURES_DIR = OUTPUT_DIR / "figures"
DATA_OUT_DIR = OUTPUT_DIR / "data"

# Sampling frequencies (Hz)
SFREQ = {
    "eeg": 512,
    "ecg": 250,
    "emg": 250,
    "fnirs": 16,
}

# Channel names
CHANNELS = {
    "eeg": ["AF7", "AF8", "F3", "F4", "PO7", "PO8", "PO3", "PO4"],
    "ecg": ["ECG"],
    "emg": ["EMG"],
    "fnirs": ["HbO", "HbR"],
}

# Nyquist validation: max expected signal frequencies (Hz)
NYQUIST_MAX_FREQ = {
    "eeg": 50,  # EEG typically < 50 Hz
    "ecg": 40,  # QRS complex < 40 Hz
    "emg": 100,  # EMG typically < 100 Hz
    "fnirs": 2,  # fNIRS hemodynamics < 0.5 Hz (use 2 for safety)
}
