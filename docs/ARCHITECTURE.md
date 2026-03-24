# Architecture

## Project Structure

```
biosignal_processing/
├── scripts/
│   └── run_pipeline.py          # single entry point
├── src/
│   ├── __init__.py
│   ├── config.py                # paths, constants
│   └── stages/
│       ├── __init__.py
│       ├── 01_acquisition.py
│       ├── 02_sqi.py
│       ├── 03_statistics.py
│       ├── 04_cleaning.py
│       ├── 05_segmentation.py
│       ├── 06_features.py
│       ├── 07_engineering.py
│       ├── 08_dimreduction.py
│       ├── 09_selection.py
│       └── 10_validation.py
└── output/
    ├── metrics/
    ├── figures/
    └── data/
```

## Pipeline Execution

Single entry point, sequential execution:

```bash
uv run python scripts/run_pipeline.py
```

## Stage Structure

Each stage follows the same pattern:

```python
# src/stages/02_sqi.py
"""Stage 2: Signal Quality Index."""
import json
from ..config import DATA_DIR, METRICS_DIR, FIGURES_DIR

def run():
    print("  [2/10] Running SQI...")
    # ... logic ...
    # Save metrics to METRICS_DIR / "sqi_metrics.json"
    # Save figures to FIGURES_DIR / "sqi_analysis.png"

if __name__ == "__main__":
    run()
```

## Output Structure

```
output/
├── metrics/
│   ├── sqi_metrics.json
│   ├── statistics.json
│   ├── cleaning_validation.json
│   ├── segmentation_metrics.json
│   ├── pca_results.json
│   ├── feature_ranking.json
│   └── final_validation.json
├── figures/
│   ├── sqi_analysis.png
│   ├── histogram.png
│   ├── boxplot.png
│   └── ...
└── data/
    ├── features.csv
    ├── features_engineered.csv
    └── dataset_final.csv
```

## Pipeline Stages

| # | Stage | Output |
|---|-------|--------|
| 1 | Acquisition | Raw signal files |
| 2 | SQI | `metrics/sqi_metrics.json` |
| 3 | Statistics | `metrics/statistics.json` |
| 4 | Cleaning | `metrics/cleaning_validation.json` |
| 5 | Segmentation | `metrics/segmentation_metrics.json` |
| 6 | Features | `data/features.csv` |
| 7 | Engineering | `data/features_engineered.csv` |
| 8 | Dimensionality Reduction | `metrics/pca_results.json` |
| 9 | Feature Selection | `metrics/feature_ranking.json` |
| 10 | Validation | `metrics/final_validation.json` + `data/dataset_final.csv` |
