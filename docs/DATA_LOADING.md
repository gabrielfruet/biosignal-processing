# Data Loading Specification

This document describes the libraries and methods used for loading biosignal data in the `scripts/ieee/` directory.

## Libraries

| Library | Purpose |
|---------|---------|
| `pandas` | CSV file loading |
| `numpy` | CSV file loading, array manipulation |
| `mne` | SNIRF file loading, RawArray creation |
| `os` | Path manipulation |

## File Types and Loading Methods

### ECG (`scripts/ieee/ecg.py`)

```python
import pandas as pd
import mne

# Data files
ecg_data = pd.read_csv(ecg_file_path).values.T

# Markers
index_data = pd.read_csv(index_file_path, header=None)
```

### EEG (`scripts/ieee/eeg.py`)

```python
import numpy as np
import mne

# Data files
data = np.genfromtxt(file_path, delimiter=',', skip_header=1, dtype='float64', missing_values='', filling_values=np.nan)

# Markers
data_M = np.loadtxt(file_path_mark, delimiter=',', skiprows=5, dtype='str')
```

### EMG (`scripts/ieee/emg.py`)

```python
import pandas as pd
import mne

# Data files
emg_data = pd.read_csv(emg_file_path).values.T

# Markers
index_data = pd.read_csv(index_file_path, header=None)
```

### fNIRS (`scripts/ieee/fnirs.py`)

```python
import pandas as pd
import mne
from mne.preprocessing.nirs import beer_lambert_law, optical_density

# SNIRF files
raw_intensity = read_raw_snirf(nirs_file_path, preload=True)
raw_od = optical_density(raw_intensity)
raw_hb = beer_lambert_law(raw_od)

# Markers
index_data = pd.read_csv(index_file_path, header=None)
```

## File Formats

| Signal | Data Format | Markers Format |
|--------|-------------|----------------|
| ECG | CSV | CSV |
| EEG | CSV | CSV |
| EMG | CSV | CSV |
| fNIRS | SNIRF | CSV |

## Data Directory Structure

```
DATA_DIR/
├── 000/
│   ├── 000_ECG.csv
│   ├── 000_EEG.csv
│   ├── 000_EMG.csv
│   ├── 000_MARKERS.csv
│   └── 000.snirf
├── 001/
│   └── ...
└── 028/
```
