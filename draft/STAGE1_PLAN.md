# Plan: Stage 1 - Biosignal Acquisition

## Overview

Execute the first stage of the biosignal processing pipeline as defined in `docs/PRD.md`. This stage focuses on acquiring raw biosignal data, validating acquisition parameters, and documenting the experimental protocol.

---

## 1. Project Structure Setup

Create the following directory structure under `src/biosignal/`:

```
src/biosignal/
├── __init__.py
├── config.py              # Centralized paths and constants
├── io/
│   ├── __init__.py
│   └── ieee.py            # Ported data loader (16 subjects)
└── stages/
    ├── __init__.py
    └── 01_acquisition.py   # Stage 1 implementation

output/
├── metrics/
├── figures/
└── data/
```

**Files to create:**
- `src/biosignal/__init__.py`
- `src/biosignal/config.py`
- `src/biosignal/io/__init__.py`
- `src/biosignal/io/ieee.py`
- `src/biosignal/stages/__init__.py`
- `src/biosignal/stages/01_acquisition.py`

---

## 2. Update `pyproject.toml`

Add package configuration for src layout and Typer dependency:

```toml
[project]
name = "biosignal-processing"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "pyqt6>=6.10.2",
    "mne>=1.6.0",
    "typer>=0.12",
]

[tool.hatch.build.targets.wheels]
packages = ["src/biosignal"]
```

---

## 3. Implement `src/biosignal/config.py`

Centralized configuration constants:

```python
from pathlib import Path

# Directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "ieee-multimodal"
CACHE_DIR = PROJECT_ROOT / "data" / "ieee-multimodal-extracted"
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
    "eeg": 50,      # EEG typically < 50 Hz
    "ecg": 40,      # QRS complex < 40 Hz
    "emg": 100,     # EMG typically < 100 Hz
    "fnirs": 2,     # fNIRS hemodynamics < 0.5 Hz (use 2 for safety)
}
```

---

## 4. Implement `src/biosignal/io/ieee.py`

Port the existing loader from `scripts/load_ieee_multimodal.py`:

### Functions to Implement

| Function | Purpose |
|----------|---------|
| `_get_subject_dir(subject_id)` | Extract zip to cache if needed, return path |
| `_load_markers(subject_dir)` | Parse MARKERS.csv → dict with baseline/stim_start/stim_end |
| `_load_eeg(subject_dir)` | Load EEG CSV, return MNE RawArray (8 ch, 512 Hz) |
| `_load_ecg(subject_dir)` | Load ECG CSV, return MNE RawArray (1 ch, 250 Hz) |
| `_load_emg(subject_dir)` | Load EMG CSV, return MNE RawArray (1 ch, 250 Hz) |
| `_load_fnirs(subject_dir)` | Load SNIRF, apply Beer-Lambert, return HbO/HbR RawArray (16 Hz) |
| `list_subjects()` | Return [0, 1, 2, ..., 15] |
| `load(subject_id, modalities)` | Unified loader returning dict of Raw + markers |
| `load_raw(subject_id, modality)` | Convenience: single modality as Raw |

### Marker Structure
```python
{
    "baseline": {"eeg": 0, "ecg": 0, "emg": 0, "fnirs": 0},
    "stim_start": {"eeg": 15360, "ecg": 7680, ...},
    "stim_end": {"eeg": 30720, "ecg": 15360, ...},
}
```

---

## 5. Implement `src/biosignal/stages/01_acquisition.py`

### Functions to Implement

| Function | Purpose |
|----------|---------|
| `validate_nyquist(sfreq, modality)` | Check `sfreq >= 2 * NYQUIST_MAX_FREQ[modality]` |
| `identify_problems(raw)` | Detect flat lines, clipping, dead channels, dropouts |
| `document_protocol()` | Return protocol metadata dict |
| `document_hardware()` | Return hardware specs per modality |
| `plot_raw_signals(data, subject_id, problems)` | Generate multi-panel visualization |
| `plot_overview(all_data)` | Generate 4x4 grid overview |
| `run()` | Execute full stage |

### Problem Detection

| Problem | Detection Method |
|---------|------------------|
| Flat line | Std dev < 1e-6 |
| Clipping | >5% samples at min or max value |
| Dead channel | All values identical |
| Excessive noise | Variance > 3× median variance across channels |
| Dropout | >1s gap with signal change < 0.1% |

### Protocol Documentation
```python
{
    "dataset": "IEEE Multimodal Emotion Recognition",
    "subjects": 16,
    "subject_ids": [0, 1, 2, ..., 15],
    "task_type": "emotion_induction",
    "baseline_duration_s": 30,
    "stimulation_duration_s": 30,
    "total_duration_s": 60,
    "intervals": ["baseline", "stimulation", "recovery"],
}
```

### Hardware Documentation
```python
{
    "eeg": {
        "channels": 8,
        "sfreq_hz": 512,
        "channel_names": ["AF7", "AF8", "F3", "F4", "PO7", "PO8", "PO3", "PO4"],
        "system": "Emotiv EPOC+",
    },
    "ecg": {
        "channels": 1,
        "sfreq_hz": 250,
    },
    "emg": {
        "channels": 1,
        "sfreq_hz": 250,
    },
    "fnirs": {
        "channels": 2,
        "measures": ["HbO", "HbR"],
        "sfreq_hz": 16,
        "transformation": "Beer-Lambert Law",
    },
}
```

---

## 6. Visualization Specifications

### Individual Subject Plot: `output/figures/s{subject_id:03d}_raw_signals.png`

**Layout: 4 rows × 2 columns**

| Row | Modality | Duration | Notes |
|-----|----------|----------|-------|
| 1 | EEG (8 channels stacked) | 5 seconds | Label each channel |
| 2 | ECG | 10 seconds | Show R-peak visibility |
| 3 | EMG | 5 seconds | Show muscle burst patterns |
| 4 | fNIRS (HbO + HbR) | 30 seconds | Overlay both channels |

**Annotations:**
- 🔴 Red boxes = problem regions
- Vertical dashed line = stimulus onset
- Grid lines for time reference

**Quality:**
- High DPI (300)
- Clear axis labels with units
- Legend for fNIRS channels

### Overview Plot: `output/figures/overview_all_subjects.png`

**Layout: 4×4 grid (16 subjects)**

- 3 seconds of EEG from each subject
- Channel AF7 shown (or first available)
- Problematic subjects: red border
- Subject ID label in each panel

---

## 7. Output Files

### `output/data/acquisition_metadata.json`
```json
{
    "dataset": "IEEE Multimodal Emotion Recognition",
    "protocol": { ... },
    "hardware": { ... },
    "nyquist_validation": {
        "eeg": {"sfreq": 512, "max_freq": 50, "ratio": 10.24, "compliant": true},
        "ecg": {"sfreq": 250, "max_freq": 40, "ratio": 6.25, "compliant": true},
        "emg": {"sfreq": 250, "max_freq": 100, "ratio": 2.5, "compliant": true},
        "fnirs": {"sfreq": 16, "max_freq": 2, "ratio": 8, "compliant": true}
    }
}
```

### `output/metrics/s{subject_id:03d}_acquisition.json` (per subject)
```json
{
    "subject_id": 0,
    "modalities": {
        "eeg": {
            "channels": 8,
            "samples": 30720,
            "duration_s": 60,
            "problems": {
                "flat_channels": [],
                "clipping_channels": [],
                "dead_channels": [],
                "noisy_channels": ["F4"]
            }
        },
        "ecg": { ... },
        "emg": { ... },
        "fnirs": { ... }
    }
}
```

### `output/metrics/acquisition_summary.json`
```json
{
    "total_subjects": 16,
    "subjects_with_problems": 3,
    "problem_summary": {
        "flat_channels": 0,
        "clipping_channels": 1,
        "dead_channels": 0,
        "noisy_channels": 4
    }
}
```

---

## 8. CLI with Typer (`src/biosignal/cli.py`)

Entry point using Typer for beautiful CLI:

```python
#!/usr/bin/env python3
"""Biosignal Processing Pipeline CLI."""
import typer
from typing import Optional
from biosignal.stages import acquisition

app = typer.Typer(
    name="biosignal",
    help="Biosignal Processing Pipeline",
    add_completion=False,
)

STAGE_NAMES = {
    1: "acquisition",
    2: "sqi",
    3: "statistics",
    4: "cleaning",
    5: "segmentation",
    6: "features",
    7: "engineering",
    8: "dimreduction",
    9: "selection",
    10: "validation",
}


@app.command()
def run(
    stage: int = typer.Argument(1, help="Stage number (1-10)"),
    subject: Optional[int] = typer.Option(None, help="Process specific subject only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run a pipeline stage."""
    typer.echo(f"Running stage {stage}: {STAGE_NAMES.get(stage, 'unknown')}")

    if stage == 1:
        acquisition.run(subject_id=subject, verbose=verbose)
    else:
        typer.echo(f"Stage {stage} not yet implemented", err=True)


@app.command()
def list_stages():
    """List all available pipeline stages."""
    typer.secho("Available stages:", bold=True)
    for num, name in STAGE_NAMES.items():
        typer.echo(f"  {num}. {name}")


@app.command()
def info(
    subject: Optional[int] = typer.Option(None, help="Subject ID"),
):
    """Show dataset information."""
    from biosignal.io import ieee

    subjects = ieee.list_subjects()
    typer.secho("IEEE Multimodal Biosignal Dataset", bold=True, fg=typer.colors.CYAN)
    typer.echo(f"Total subjects: {len(subjects)}")
    typer.echo(f"Subject IDs: {subjects}")

    if subject is not None:
        if subject not in subjects:
            typer.echo(f"Subject {subject} not found", err=True)
            raise typer.Exit(code=1)
        data = ieee.load(subject)
        typer.secho(f"\nSubject {subject:03d}:", bold=True)
        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality in data:
                info = data[modality]
                typer.echo(f"  {modality.upper()}: {info['sfreq']} Hz, {len(info['ch_names'])} ch")


if __name__ == "__main__":
    app()
```

**Alternative: Rich Typer with subcommands per stage**

```python
"""CLI with separate subapps per stage (optional pattern)."""
import typer

app = typer.Typer()

@app.command()
def acquisition(
    subject: Optional[int] = typer.Option(None, help="Process specific subject"),
):
    """Stage 1: Biosignal Acquisition."""
    from biosignal.stages import acquisition
    acquisition.run(subject_id=subject)

@app.command()
def sqi(
    subject: Optional[int] = typer.Option(None, help="Process specific subject"),
):
    """Stage 2: Signal Quality Index."""
    typer.echo("Stage 2 not yet implemented")

# ... similar for other stages
```

**Usage:**
```bash
# Run all (default: stage 1)
uv run python -m biosignal run 1

# Run with specific subject
uv run python -m biosignal run 1 --subject 5

# Verbose mode
uv run python -m biosignal run 1 --subject 5 --verbose

# List stages
uv run python -m biosignal list-stages

# Info about dataset
uv run python -m biosignal info
uv run python -m biosignal info --subject 0

# Help
uv run python -m biosignal --help
uv run python -m biosignal run --help
```

---

## 9. Dependencies

Required packages (add to `pyproject.toml` if missing):
- `typer[all]>=0.12`  # Includes rich for better formatting
- `numpy>=1.24`
- `pandas>=2.0`
- `matplotlib>=3.7`
- `mne>=1.6`
- `scipy>=1.11`

---

## 10. Execution Steps

1. **Create directories**
   ```bash
   mkdir -p src/biosignal/io src/biosignal/stages output/metrics output/figures output/data
   ```

2. **Update `pyproject.toml`** with Typer dependency and package config

3. **Create `src/biosignal/__init__.py`**
   ```python
   """BioSignal Processing Pipeline."""
   __version__ = "0.1.0"
   ```

4. **Create `src/biosignal/config.py`**

5. **Create `src/biosignal/io/__init__.py`**
   ```python
   """I/O utilities for biosignal data."""
   from .ieee import load, list_subjects, load_raw
   ```

6. **Create `src/biosignal/io/ieee.py`** (ported loader)

7. **Create `src/biosignal/stages/__init__.py`**
   ```python
   """Pipeline stages."""
   ```

8. **Create `src/biosignal/stages/01_acquisition.py`**

9. **Create `src/biosignal/cli.py`** with Typer

10. **Run pipeline**
    ```bash
    uv run python -m biosignal run 1
    uv run python -m biosignal info
    ```

---

## 11. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Package imports correctly | `python -c "from biosignal import io; print(io.list_subjects())"` |
| 2 | All 16 subjects available | Returns `[0, 1, ..., 15]` |
| 3 | Data loader works | `load(0)` returns dict with eeg, ecg, emg, fnirs, markers |
| 4 | Nyquist validation passes | All modalities compliant |
| 5 | Protocol documented | JSON contains baseline/stim durations |
| 6 | Hardware documented | JSON contains specs per modality |
| 7 | Problem detection works | JSON flags known issues |
| 8 | 16 individual plots generated | `s000_raw_signals.png` through `s015_raw_signals.png` |
| 9 | Overview plot generated | `overview_all_subjects.png` exists |
| 10 | Metrics saved | `s{subject_id:03d}_acquisition.json` for all 16 |
| 11 | Metadata saved | `acquisition_metadata.json` and `acquisition_summary.json` |
| 12 | CLI works with Typer | `python -m biosignal --help` shows commands |
| 13 | Stage-specific subject works | `python -m biosignal run 1 --subject 5` processes one subject |

---

## 12. Deliverables (Stage 1)

| Deliverable | Path |
|-------------|------|
| Acquisition Metadata | `output/data/acquisition_metadata.json` |
| Per-Subject Metrics (16 files) | `output/metrics/s{000-015}_acquisition.json` |
| Summary Metrics | `output/metrics/acquisition_summary.json` |
| Raw Signal Plots (16 files) | `output/figures/s{000-015}_raw_signals.png` |
| Overview Plot | `output/figures/overview_all_subjects.png` |

---

## 13. Next Stages Preview

| Stage | Name | Prerequisites |
|-------|------|---------------|
| 2 | Signal Quality Index (SQI) | Stage 1 output |
| 3 | Initial Statistical Analysis | Stage 2 output |
| ... | ... | ... |
| 10 | Final Validation | Stages 1-9 output |
