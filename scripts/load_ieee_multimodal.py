"""Load IEEE Multimodal Biosignal Dataset.

A unified loader for EEG, ECG, EMG, and fNIRS data from the IEEE Multimodal
Emotion Recognition dataset.

Usage:
    from scripts.load_ieee_multimodal import load, list_subjects

    subjects = list_subjects()          # [0, 1, 2, ..., 15]
    data = load(0)                       # Load all modalities
    data = load(0, modalities=["eeg", "ecg"])  # Load specific modalities
"""

from pathlib import Path
import zipfile
import os
import shutil

import numpy as np
import pandas as pd
import mne
from mne import create_info
from mne.io import RawArray, read_raw_snirf


DATA_DIR = Path(__file__).parent.parent / "data" / "ieee-multimodal"
CACHE_DIR = Path(__file__).parent.parent / "data" / "ieee-multimodal-extracted"

# Sampling rates for each modality
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
    "fnirs": ["HbO", "HbR"],  # After Beer-Lambert transformation
}


def _get_subject_dir(subject_id: int) -> Path:
    """Get or extract subject directory."""
    subject_str = f"{subject_id:03d}"
    zip_path = DATA_DIR / f"{subject_str}.zip"
    extracted_dir = CACHE_DIR / subject_str

    # If already extracted, return cached directory
    if extracted_dir.exists():
        return extracted_dir

    # Extract zip file
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(CACHE_DIR)

    return extracted_dir


def _load_markers(subject_dir: Path) -> dict:
    """Load stimulus timing markers from MARKERS.csv.

    Returns dict with keys: baseline, stim_start, stim_end
    Values are tuples of (modality, sample_index) for each event.
    """
    subject_str = subject_dir.name
    marker_path = subject_dir / f"{subject_str}_MARKERS.csv"

    if not marker_path.exists():
        raise FileNotFoundError(f"MARKERS.csv not found: {marker_path}")

    # Parse markers file - format is: (empty), event_name
    #                        or: modality, index
    # Skip empty rows and rows with only event names
    df = pd.read_csv(marker_path, header=None, skip_blank_lines=True)

    # Filter out empty rows and rows where second column is empty
    df = df.dropna(how="all")
    df = df[df.iloc[:, 1].notna()]

    markers = {
        "baseline": {},  # Beginning baseline
        "stim_start": {},  # Beginning of stimulation
        "stim_end": {},  # End of stimulation
    }

    current_event = None

    for _, row in df.iterrows():
        first_col = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        second_col = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        # Check if this is an event header row (first column is empty)
        if first_col == "" and second_col != "":
            # This is an event name
            if "baseline" in second_col.lower():
                current_event = "baseline"
            elif (
                "stimulating" in second_col.lower()
                and "beginning" in second_col.lower()
            ):
                current_event = "stim_start"
            elif "stimulating" in second_col.lower() and "ending" in second_col.lower():
                current_event = "stim_end"
        # Otherwise it's a modality, index row
        elif first_col != "" and second_col != "" and current_event is not None:
            modality = first_col
            index = int(second_col)
            markers[current_event][modality] = index

    return markers


def _load_eeg(subject_dir: Path) -> dict:
    """Load EEG data."""
    subject_str = subject_dir.name
    file_path = subject_dir / f"{subject_str}_EEG.csv"

    # Load CSV (skip header)
    data = np.genfromtxt(
        file_path,
        delimiter=",",
        skip_header=1,
        dtype="float64",
        missing_values="",
        filling_values=np.nan,
    )
    # Remove rows with NaN
    data = data[~np.isnan(data).any(axis=1)]

    # Create MNE Raw object
    ch_names = [f"EEG_{ch}" for ch in CHANNELS["eeg"]]
    info = create_info(ch_names=ch_names, sfreq=SFREQ["eeg"], ch_types="eeg")
    raw = RawArray(data.T, info)

    return {
        "data": raw,
        "sfreq": SFREQ["eeg"],
        "ch_names": ch_names,
    }


def _load_ecg(subject_dir: Path) -> dict:
    """Load ECG data."""
    subject_str = subject_dir.name
    file_path = subject_dir / f"{subject_str}_ECG.csv"

    # Load CSV
    data = pd.read_csv(file_path).values.T

    # Create MNE Raw object
    ch_names = CHANNELS["ecg"]
    info = create_info(ch_names=ch_names, sfreq=SFREQ["ecg"], ch_types="ecg")
    raw = RawArray(data, info)

    return {
        "data": raw,
        "sfreq": SFREQ["ecg"],
        "ch_names": ch_names,
    }


def _load_emg(subject_dir: Path) -> dict:
    """Load EMG data."""
    subject_str = subject_dir.name
    file_path = subject_dir / f"{subject_str}_EMG.csv"

    # Load CSV
    data = pd.read_csv(file_path).values.T

    # Create MNE Raw object
    ch_names = CHANNELS["emg"]
    info = create_info(ch_names=ch_names, sfreq=SFREQ["emg"], ch_types="emg")
    raw = RawArray(data, info)

    return {
        "data": raw,
        "sfreq": SFREQ["emg"],
        "ch_names": ch_names,
    }


def _load_fnirs(subject_dir: Path) -> dict:
    """Load fNIRS data (HbO and HbR concentrations)."""
    subject_str = subject_dir.name
    file_path = subject_dir / f"{subject_str}.snirf"

    if not file_path.exists():
        raise FileNotFoundError(f"SNIRF file not found: {file_path}")

    # Load SNIRF and apply Beer-Lambert law
    raw_intensity = read_raw_snirf(file_path, preload=True)
    raw_od = mne.preprocessing.nirs.optical_density(raw_intensity)
    raw_hb = mne.preprocessing.nirs.beer_lambert_law(raw_od)

    # Get HbO and HbR channels (indices vary by channel count)
    # Typically: HbO at indices 1, 3, 5, ... and HbR at indices 25, 27, 29, ...
    # For simplicity, take first HbO and first HbR
    n_channels = raw_hb.get_data().shape[0]

    # Find HbO and HbR channels
    hbo_idx = None
    hbr_idx = None

    for i, ch in enumerate(raw_hb.ch_names):
        if "HbO" in ch and hbo_idx is None:
            hbo_idx = i
        if "HbR" in ch and hbr_idx is None:
            hbr_idx = i

    # Fallback: use hardcoded indices from original script
    if hbo_idx is None:
        hbo_idx = 1
    if hbr_idx is None:
        hbr_idx = 25

    # Extract data
    data = raw_hb.get_data()[[hbo_idx, hbr_idx]]

    # Create new Raw object with just HbO and HbR
    ch_names = ["HbO", "HbR"]
    ch_types = ["hbo", "hbr"]
    info = create_info(ch_names=ch_names, sfreq=SFREQ["fnirs"], ch_types=ch_types)
    raw = RawArray(data, info)

    return {
        "data": raw,
        "sfreq": SFREQ["fnirs"],
        "ch_names": ch_names,
    }


def list_subjects() -> list[int]:
    """List available subject IDs.

    Returns:
        List of subject IDs (0-15).
    """
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    subjects = []
    for f in DATA_DIR.iterdir():
        if f.suffix == ".zip" and f.stem.isdigit():
            subjects.append(int(f.stem))

    return sorted(subjects)


def get_markers(subject_id: int) -> dict:
    """Get stimulus timing markers for a subject.

    Args:
        subject_id: Subject ID (0-15).

    Returns:
        Dictionary with 'baseline', 'stim_start', 'stim_end' keys,
        each containing a dict of modality -> sample index.
    """
    subject_dir = _get_subject_dir(subject_id)
    return _load_markers(subject_dir)


def load(subject_id: int, modalities: list[str] | None = None) -> dict:
    """Load biosignal data for a subject.

    Args:
        subject_id: Subject ID (0-15).
        modalities: List of modalities to load. Options: 'eeg', 'ecg', 'emg',
                    'fnirs'. If None, loads all available modalities.

    Returns:
        Dictionary with modality keys ('eeg', 'ecg', 'emg', 'fnirs'), each
        containing:
        - 'data': MNE Raw object
        - 'sfreq': Sampling frequency (Hz)
        - 'ch_names': List of channel names

        Also includes 'markers' key with stimulus timing information.

    Example:
        >>> data = load(0)
        >>> eeg_raw = data["eeg"]["data"]
        >>> eeg_raw.filter(5, 40)  # Apply bandpass filter
    """
    available_modalities = ["eeg", "ecg", "emg", "fnirs"]

    if modalities is None:
        modalities = available_modalities
    else:
        # Validate modalities
        for mod in modalities:
            if mod not in available_modalities:
                raise ValueError(
                    f"Unknown modality: {mod}. Available: {available_modalities}"
                )

    # Get subject directory (auto-extracts if needed)
    subject_dir = _get_subject_dir(subject_id)

    # Load markers
    markers = _load_markers(subject_dir)

    # Load requested modalities
    result = {"markers": markers}

    loaders = {
        "eeg": _load_eeg,
        "ecg": _load_ecg,
        "emg": _load_emg,
        "fnirs": _load_fnirs,
    }

    for modality in modalities:
        try:
            result[modality] = loaders[modality](subject_dir)
        except FileNotFoundError as e:
            print(f"Warning: Could not load {modality} for subject {subject_id}: {e}")

    return result


def load_raw(subject_id: int, modality: str) -> mne.io.Raw:
    """Convenience function to load a single modality as Raw object.

    Args:
        subject_id: Subject ID (0-15).
        modality: Modality to load ('eeg', 'ecg', 'emg', 'fnirs').

    Returns:
        MNE Raw object.
    """
    data = load(subject_id, modalities=[modality])
    return data[modality]["data"]


def main():
    """Example usage."""
    print("=== IEEE Multimodal Biosignal Dataset Loader ===\n")
    print(f"Data directory: {DATA_DIR}\n")

    # List available subjects
    subjects = list_subjects()
    print(f"Available subjects ({len(subjects)}): {subjects}\n")

    # Load sample subject
    subject_id = subjects[0]
    print(f"Loading subject {subject_id}...")

    data = load(subject_id)

    print(f"\nLoaded modalities: {[k for k in data.keys() if k != 'markers']}")

    for modality in ["eeg", "ecg", "emg", "fnirs"]:
        if modality in data:
            info = data[modality]
            print(f"\n{modality.upper()}:")
            print(f"  - Sampling frequency: {info['sfreq']} Hz")
            print(f"  - Channels: {info['ch_names']}")
            print(f"  - Samples: {info['data'].get_data().shape[1]}")

    print(f"\nMarkers:")
    print(f"  Baseline: {data['markers']['baseline']}")
    print(f"  Stimulus start: {data['markers']['stim_start']}")
    print(f"  Stimulus end: {data['markers']['stim_end']}")


if __name__ == "__main__":
    main()
