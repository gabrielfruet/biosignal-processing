
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_clipping(subject_id):
    subject_str = f"{subject_id:03d}"
    data_dir = Path("data/ieee-multimodal-extracted") / subject_str
    
    results = {}
    
    # Analyze ECG
    ecg_path = data_dir / f"{subject_str}_ECG.csv"
    if ecg_path.exists():
        df = pd.read_csv(ecg_path)
        data = df.values.flatten()
        min_val, max_val = data.min(), data.max()
        range_val = max_val - min_val
        clip_threshold_low = min_val + 0.001 * range_val
        clip_threshold_high = max_val - 0.001 * range_val
        clipped_count = np.sum((data <= clip_threshold_low) | (data >= clip_threshold_high))
        perc = clipped_count / len(data)
        results['ecg'] = {
            'min': float(min_val),
            'max': float(max_val),
            'clipped_perc': float(perc),
            'is_clipped': bool(perc > 0.05)
        }

    # Analyze EMG
    emg_path = data_dir / f"{subject_str}_EMG.csv"
    if emg_path.exists():
        df = pd.read_csv(emg_path)
        data = df.values.flatten()
        min_val, max_val = data.min(), data.max()
        range_val = max_val - min_val
        clip_threshold_low = min_val + 0.001 * range_val
        clip_threshold_high = max_val - 0.001 * range_val
        clipped_count = np.sum((data <= clip_threshold_low) | (data >= clip_threshold_high))
        perc = clipped_count / len(data)
        results['emg'] = {
            'min': float(min_val),
            'max': float(max_val),
            'clipped_perc': float(perc),
            'is_clipped': bool(perc > 0.05)
        }
        
    return results

if __name__ == "__main__":
    import json
    print(json.dumps(analyze_clipping(0), indent=2))
