"""Centralized configuration constants for biosignal processing."""

from pathlib import Path

# Directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ieee-multimodal-extracted"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Stage-specific directories
METRICS_DIR = OUTPUT_DIR / "metrics"  # Legacy, still used for global metrics
FIGURES_DIR = OUTPUT_DIR / "figures"  # Legacy, still used for global figures
DATA_OUT_DIR = OUTPUT_DIR / "data"

# Stage 1: Acquisition
STAGE1_DIR = OUTPUT_DIR / "stage1_acquisition"
STAGE1_METRICS_DIR = STAGE1_DIR / "metrics"
STAGE1_FIGURES_DIR = STAGE1_DIR / "figures"

# Stage 2: SQI
STAGE2_DIR = OUTPUT_DIR / "stage2_sqi"
STAGE2_METRICS_DIR = STAGE2_DIR / "metrics"
STAGE2_FIGURES_DIR = STAGE2_DIR / "figures"

# Stage 3: Statistics
STAGE3_DIR = OUTPUT_DIR / "stage3_statistics"
STAGE3_METRICS_DIR = STAGE3_DIR / "metrics"
STAGE3_FIGURES_DIR = STAGE3_DIR / "figures"

# Stage 4: Cleaning
STAGE4_DIR = OUTPUT_DIR / "stage4_cleaning"
STAGE4_METRICS_DIR = STAGE4_DIR / "metrics"
STAGE4_FIGURES_DIR = STAGE4_DIR / "figures"
STAGE4_DATA_DIR = STAGE4_DIR / "data"

# Stage 5: Segmentation
STAGE5_DIR = OUTPUT_DIR / "stage5_segmentation"
STAGE5_METRICS_DIR = STAGE5_DIR / "metrics"
STAGE5_FIGURES_DIR = STAGE5_DIR / "figures"
STAGE5_DATA_DIR = STAGE5_DIR / "data" / "segments"

# Stage 6: Feature Extraction
STAGE6_DIR = OUTPUT_DIR / "stage6_features"
STAGE6_METRICS_DIR = STAGE6_DIR / "metrics"
STAGE6_FIGURES_DIR = STAGE6_DIR / "figures"
STAGE6_DATA_DIR = STAGE6_DIR / "data"

# Stage 7: Feature Engineering
STAGE7_DIR = OUTPUT_DIR / "stage7_engineering"
STAGE7_METRICS_DIR = STAGE7_DIR / "metrics"
STAGE7_FIGURES_DIR = STAGE7_DIR / "figures"
STAGE7_DATA_DIR = STAGE7_DIR / "data"

# Stage 8: Dimensionality Reduction
STAGE8_DIR = OUTPUT_DIR / "stage8_dimreduction"
STAGE8_METRICS_DIR = STAGE8_DIR / "metrics"
STAGE8_FIGURES_DIR = STAGE8_DIR / "figures"
STAGE8_DATA_DIR = STAGE8_DIR / "data"

# Stage 9: Feature Selection
STAGE9_DIR = OUTPUT_DIR / "stage9_selection"
STAGE9_METRICS_DIR = STAGE9_DIR / "metrics"
STAGE9_FIGURES_DIR = STAGE9_DIR / "figures"
STAGE9_DATA_DIR    = STAGE9_DIR / "data"

# Stage 10: Final Validation
STAGE10_DIR = OUTPUT_DIR / "stage10_validation"
STAGE10_METRICS_DIR = STAGE10_DIR / "metrics"
STAGE10_FIGURES_DIR = STAGE10_DIR / "figures"
STAGE10_DATA_DIR    = STAGE10_DIR / "data"

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

# Segmentation configuration
SEGMENTATION_CONFIG = {
    "window_sizes": {
        "eeg": {"fixed_1s": 512, "fixed_5s": 2560},
        "ecg": {"fixed_1s": 250, "fixed_5s": 1250},
        "emg": {"fixed_1s": 250, "fixed_5s": 1250},
        "fnirs": {"fixed_1s": 16, "fixed_5s": 80},
    },
    "overlap_options": [0.0, 0.25, 0.5],
    "default_window": 5,  # seconds
    "stability_threshold_cv": 0.30,  # CV < 30% = stable
}

# Event-based segmentation markers
EVENT_WINDOW_CONFIG = {
    "baseline": {"before": 0, "after": 30},  # 30s baseline window
    "stimulation": {"before": 0, "after": 30},  # 30s stimulation window
    "recovery": {"before": 0, "after": 30},  # 30s recovery window
}
