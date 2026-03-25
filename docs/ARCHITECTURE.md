# Architecture

## Project Structure

```
biosignal_processing/
├── src/
│   └── biosignal/               # Importable package
│       ├── __init__.py
│       ├── config.py            # paths, constants
│       ├── cli.py               # Typer CLI entry point
│       ├── io/
│       │   ├── __init__.py
│       │   └── ieee.py          # IEEE dataset loader
│       └── stages/
│           ├── __init__.py
│           ├── 01_acquisition.py
│           ├── 02_sqi.py
│           ├── 03_statistics.py
│           ├── 04_cleaning.py
│           ├── 05_segmentation.py
│           ├── 06_features.py
│           ├── 07_engineering.py
│           ├── 08_dimreduction.py
│           ├── 09_selection.py
│           └── 10_validation.py
├── output/
│   ├── metrics/
│   ├── figures/
│   └── data/
└── docs/
```

## CLI (Typer)

The pipeline uses [Typer](https://typer.tiangolo.com/) for a modern CLI experience.

### Installation

Dependencies are managed via `pyproject.toml`:

```toml
[project]
dependencies = [
    "typer>=0.12",
    "mne>=1.6.0",
]
```

### CLI Entry Point

```bash
# As module
uv run python -m biosignal --help

# Or via direct script (if configured)
```

### Commands

| Command | Description |
|---------|-------------|
| `run <stage>` | Run a pipeline stage (1-10) |
| `list-stages` | Show all available stages |
| `info` | Show dataset information |
| `info --subject <id>` | Show specific subject details |

### Usage Examples

```bash
# Run stage 1 (acquisition) for all subjects
uv run python -m biosignal run 1

# Run stage 1 for a specific subject
uv run python -m biosignal run 1 --subject 5

# Run with verbose output
uv run python -m biosignal run 1 --subject 5 --verbose

# List all pipeline stages
uv run python -m biosignal list-stages

# Show dataset info
uv run python -m biosignal info

# Show specific subject info
uv run python -m biosignal info --subject 0
```

### CLI Implementation

```python
# src/biosignal/cli.py
import typer
from typing import Optional

app = typer.Typer(help="Biosignal Processing Pipeline")

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
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run a pipeline stage."""
    typer.echo(f"Running stage {stage}: {STAGE_NAMES.get(stage, 'unknown')}")
    # Stage implementation...

@app.command()
def list_stages():
    """List all available pipeline stages."""
    typer.secho("Available stages:", bold=True)
    for num, name in STAGE_NAMES.items():
        typer.echo(f"  {num}. {name}")

@app.command()
def info(subject: Optional[int] = None):
    """Show dataset information."""
    # Dataset info...
```

## Stage Structure

Each stage follows the same pattern:

```python
# src/biosignal/stages/02_sqi.py
"""Stage 2: Signal Quality Index."""
import json
from ..config import METRICS_DIR, FIGURES_DIR

def run(subject_id: int | None = None, verbose: bool = False):
    """Execute SQI stage.

    Args:
        subject_id: Process specific subject only (None = all subjects)
        verbose: Enable verbose output
    """
    print("  [2/10] Running SQI...")
    # ... logic ...
    # Save metrics to METRICS_DIR / "sqi_metrics.json"
    # Save figures to FIGURES_DIR / "sqi_analysis.png"
```

## Output Structure

```
output/
├── metrics/
│   ├── acquisition_summary.json
│   ├── s{000-015}_acquisition.json
│   ├── sqi_metrics.json
│   ├── statistics.json
│   ├── cleaning_validation.json
│   ├── segmentation_metrics.json
│   ├── pca_results.json
│   ├── feature_ranking.json
│   └── final_validation.json
├── figures/
│   ├── s{000-015}_raw_signals.png
│   ├── overview_all_subjects.png
│   ├── sqi_analysis.png
│   ├── histogram.png
│   ├── boxplot.png
│   └── ...
└── data/
    ├── acquisition_metadata.json
    ├── features.csv
    ├── features_engineered.csv
    └── dataset_final.csv
```

## Pipeline Stages

| # | Stage | Command | Output |
|---|-------|---------|--------|
| 1 | Acquisition | `run 1` | Raw signals, metadata |
| 2 | SQI | `run 2` | `metrics/sqi_metrics.json` |
| 3 | Statistics | `run 3` | `metrics/statistics.json` |
| 4 | Cleaning | `run 4` | `metrics/cleaning_validation.json` |
| 5 | Segmentation | `run 5` | `metrics/segmentation_metrics.json` |
| 6 | Features | `run 6` | `data/features.csv` |
| 7 | Engineering | `run 7` | `data/features_engineered.csv` |
| 8 | Dimensionality Reduction | `run 8` | `metrics/pca_results.json` |
| 9 | Feature Selection | `run 9` | `metrics/feature_ranking.json` |
| 10 | Validation | `run 10` | `metrics/final_validation.json` + `data/dataset_final.csv` |

## Data Loading (I/O)

The `io` submodule handles dataset loading:

```python
from biosignal.io import ieee

# List available subjects
subjects = ieee.list_subjects()  # [0, 1, ..., 15]

# Load all modalities for a subject
data = ieee.load(0)
# Returns: {"eeg": {...}, "ecg": {...}, "emg": {...}, "fnirs": {...}, "markers": {...}}

# Load specific modalities
data = ieee.load(0, modalities=["eeg", "ecg"])

# Load single modality as MNE Raw
raw = ieee.load_raw(0, "eeg")
```

## Configuration

Centralized in `src/biosignal/config.py`:

```python
# Sampling frequencies
SFREQ = {"eeg": 512, "ecg": 250, "emg": 250, "fnirs": 16}

# Output directories
METRICS_DIR = OUTPUT_DIR / "metrics"
FIGURES_DIR = OUTPUT_DIR / "figures"
DATA_OUT_DIR = OUTPUT_DIR / "data"
```
