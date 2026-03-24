"""IEEE Multimodal Biosignal Dataset Loader.

A unified loader for EEG, ECG, EMG, and fNIRS data from the IEEE Multimodal
Emotion Recognition dataset.

Usage:
    from biosignal.io import load, list_subjects

    subjects = list_subjects()          # [0, 1, 2, ..., 15]
    data = load(0)                      # Load all modalities
    data = load(0, modalities=["eeg", "ecg"])  # Load specific modalities
"""
# pyright: reportArgumentType=false

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import mne
from mne import create_info
from mne.io import RawArray

from biosignal.config import DATA_DIR, SFREQ, CHANNELS  # type: ignore[attr-defined]


# Type alias for loaded modality data
ModalityDict = dict[str, object]
MarkersDict = dict[str, dict[str, int]]
SubjectDict = dict[str, MarkersDict | ModalityDict]


def _get_subject_dir(subject_id: int) -> Path:
    """Get subject directory path.

    Args:
        subject_id: Subject ID (0-15).

    Returns:
        Path to subject directory.
    """
    subject_str = f"{subject_id:03d}"
    subject_dir = DATA_DIR / subject_str

    if not subject_dir.exists():
        raise FileNotFoundError(f"Subject directory not found: {subject_dir}")

    return subject_dir


def _load_markers(subject_dir: Path) -> MarkersDict:
    """Load stimulus timing markers from MARKERS.csv.

    Args:
        subject_dir: Path to subject directory.

    Returns:
        Dictionary with 'baseline', 'stim_start', 'stim_end' keys,
        each containing a dict of modality -> sample index.
    """
    subject_str = subject_dir.name
    marker_path = subject_dir / f"{subject_str}_MARKERS.csv"

    if not marker_path.exists():
        raise FileNotFoundError(f"MARKERS.csv not found: {marker_path}")

    # Parse markers file
    df = pd.read_csv(marker_path, header=None, skip_blank_lines=True)
    df = df.dropna(how="all")
    df = df[df.iloc[:, 1].notna()]

    markers: MarkersDict = {
        "baseline": {},
        "stim_start": {},
        "stim_end": {},
    }

    current_event: str | None = None

    for _, row in df.iterrows():
        first_col = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        second_col = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        if first_col == "" and second_col != "":
            if "baseline" in second_col.lower():
                current_event = "baseline"
            elif (
                "stimulating" in second_col.lower()
                and "beginning" in second_col.lower()
            ):
                current_event = "stim_start"
            elif "stimulating" in second_col.lower() and "ending" in second_col.lower():
                current_event = "stim_end"
        elif first_col != "" and second_col != "" and current_event is not None:
            modality = first_col
            index = int(second_col)
            markers[current_event][modality] = index

    return markers


def _load_eeg(subject_dir: Path) -> ModalityDict:
    """Load EEG data.

    Args:
        subject_dir: Path to subject directory.

    Returns:
        Dictionary with 'data' (Raw), 'sfreq', 'ch_names'.
    """
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


def _load_ecg(subject_dir: Path) -> ModalityDict:
    """Load ECG data.

    Args:
        subject_dir: Path to subject directory.

    Returns:
        Dictionary with 'data' (Raw), 'sfreq', 'ch_names'.
    """
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


def _load_emg(subject_dir: Path) -> ModalityDict:
    """Load EMG data.

    Args:
        subject_dir: Path to subject directory.

    Returns:
        Dictionary with 'data' (Raw), 'sfreq', 'ch_names'.
    """
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


def _load_fnirs(subject_dir: Path) -> ModalityDict:
    """Load fNIRS data (HbO and HbR concentrations).

    Args:
        subject_dir: Path to subject directory.

    Returns:
        Dictionary with 'data' (Raw), 'sfreq', 'ch_names'.
    """
    subject_str = subject_dir.name
    file_path = subject_dir / f"{subject_str}.snirf"

    if not file_path.exists():
        raise FileNotFoundError(f"SNIRF file not found: {file_path}")

    # Load SNIRF and apply Beer-Lambert law
    raw_intensity = mne.io.read_raw_snirf(file_path, preload=True)  # type: ignore[attr-defined]
    raw_od = mne.preprocessing.nirs.optical_density(raw_intensity)  # type: ignore[attr-defined]
    raw_hb = mne.preprocessing.nirs.beer_lambert_law(raw_od)  # type: ignore[attr-defined]

    # Find HbO and HbR channels
    hbo_idx: int | None = None
    hbr_idx: int | None = None

    for i, ch in enumerate(raw_hb.ch_names):
        if "HbO" in ch and hbo_idx is None:
            hbo_idx = i
        if "HbR" in ch and hbr_idx is None:
            hbr_idx = i

    # Fallback: use hardcoded indices
    if hbo_idx is None:
        hbo_idx = 1
    if hbr_idx is None:
        hbr_idx = 25

    # Extract data
    data = raw_hb.get_data()[[hbo_idx, hbr_idx]]

    # Create new Raw object with just HbO and HbR
    # Note: MNE requires 'hbo' and 'hbr' channel types for fNIRS concentration data
    ch_names = ["HbO", "HbR"]
    ch_types: tuple[str, ...] = ("hbo", "hbr")
    info = create_info(ch_names=ch_names, sfreq=SFREQ["fnirs"], ch_types=ch_types)  # noqa: PGH003
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

    subjects: list[int] = []
    for f in DATA_DIR.iterdir():
        if f.is_dir() and f.name.isdigit():
            subjects.append(int(f.name))

    return sorted(subjects)


def load(subject_id: int, modalities: list[str] | None = None) -> SubjectDict:
    """Load biosignal data for a subject.

    Args:
        subject_id: Subject ID (0-15).
        modalities: List of modalities to load. Options: 'eeg', 'ecg', 'emg',
            'fnirs'. If None, loads all available modalities.

    Returns:
        Dictionary with modality keys ('eeg', 'ecg', 'emg', 'fnirs'), each
        containing: 'data' (MNE Raw), 'sfreq', 'ch_names'.
        Also includes 'markers' key with stimulus timing information.
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

    # Get subject directory (auto-extracts if needed)
    subject_dir = _get_subject_dir(subject_id)

    # Load markers
    markers = _load_markers(subject_dir)

    # Load requested modalities
    result: SubjectDict = {"markers": markers}

    loaders: dict[str, Callable[[Path], ModalityDict]] = {
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


def load_raw(subject_id: int, modality: str) -> RawArray:
    """Convenience function to load a single modality as Raw object.

    Args:
        subject_id: Subject ID (0-15).
        modality: Modality to load ('eeg', 'ecg', 'emg', 'fnirs').

    Returns:
        MNE Raw object.
    """
    data: SubjectDict = load(subject_id, modalities=[modality])
    modality_data = cast(ModalityDict, data[modality])
    return cast(RawArray, modality_data["data"])
