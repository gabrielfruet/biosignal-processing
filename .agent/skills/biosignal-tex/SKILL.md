---
name: biosignal-tex
description: "Project-specific skill for updating the academic document (TCC) with biosignal processing pipeline results. Use this skill when the user wants to update tex/documento.tex after completing a pipeline stage. This skill dynamically analyzes JSON metrics and automatically generates appropriate .tex content with real data."
---

# Biosignal-tex Skill

## Project Context

**Pipeline:** Biosignal Processing Pipeline (BioSignal-Process)
**Document:** `tex/documento.tex` (Academic TCC document)
**Dataset:** IEEE Multimodal Emotion Recognition (16 subjects, 4 modalities)

## Pipeline Stages

| Stage | Name |
|-------|------|
| 1 | Acquisition |
| 2 | SQI (Signal Quality Index) |
| 3 | Statistics |
| 4 | Cleaning |
| 5 | Segmentation |
| 6 | Feature Extraction |
| 7-10 | Engineering/Reduction/Selection/Validation |

## Modalities

- **EEG**: 8 channels @ 512Hz (AF7, AF8, F3, F4, PO7, PO8, PO3, PO4)
- **ECG**: 1 channel @ 250Hz
- **EMG**: 1 channel @ 250Hz
- **fNIRS**: 2 channels @ 16Hz (HbO, HbR)

## Document Structure

```
tex/
├── documento.tex              # Main document
├── 1-pre-textuais/            # Pre-textual elements
├── 2-textuais/
│   ├── 3-metodologia.tex      # Methodology chapter
│   ├── 4-resultados.tex       # Results chapter
│   └── 5-conclusao.tex
└── 3-pos-textuais/            # Post-textual elements
```

---

## Workflow

### Step 1: Create Dynamic Analysis Script

When user asks to update document for Stage N, create a Python script that:
1. Reads the metrics JSON files for that stage
2. Dynamically explores the JSON structure
3. Extracts key metrics
4. Outputs a summary

```python
import json
import sys
from pathlib import Path

def analyze_stage(stage_num):
    """Dynamically analyze any stage's metrics."""
    
    # Find metrics directory
    stage_names = {
        1: "stage1_acquisition",
        2: "stage2_sqi", 
        3: "stage3_statistics",
        4: "stage4_cleaning",
        5: "stage5_segmentation",
        6: "stage6_features",
    }
    
    metrics_dir = Path(f"output/{stage_names[stage_num]}/metrics")
    
    # Find all JSON files
    json_files = list(metrics_dir.glob("*.json"))
    
    # Load first file to understand structure
    data = load_json(json_files[0])
    
    # Dynamically explore structure
    def explore(obj, path=""):
        if isinstance(obj, dict):
            for key, val in list(obj.items())[:10]:
                print(f"{path}.{key}: {type(val).__name__}")
                if isinstance(val, (dict, list)):
                    explore(val, f"{path}.{key}")
        elif isinstance(obj, list):
            print(f"{path}: list[{len(obj)}]")
    
    explore(data)
```

### Step 2: Identify Key Metrics to Extract

Based on common patterns:

| Pattern | What to Extract |
|---------|-----------------|
| Subject-based | Per-subject counts, totals, aggregates |
| Window-based | n_windows_total, n_windows_usable, rejection rates |
| Quality metrics | SNR, kurtosis, entropy, CV |
| Before/after | Improvements, reductions, Cohen's d |
| Counts | subjects, channels, samples, durations |

### Step 3: Aggregate Across Subjects

```python
# Collect metrics from all subjects
all_metrics = []
for json_file in json_files:
    data = load_json(json_file)
    # Extract based on structure
    all_metrics.append(data)

# Aggregate
def aggregate(all_metrics):
    results = {
        'total': 0,
        'usable': 0,
        'rejected': 0,
        # ... dynamic based on keys found
    }
    
    for m in all_metrics:
        # Navigate to numeric values
        def find_numbers(obj, keys):
            for key in keys:
                if isinstance(obj, dict) and key in obj:
                    obj = obj[key]
            if isinstance(obj, (int, float)):
                return obj
            return 0
        
        # Extract and accumulate
        results['total'] += find_numbers(m, ['total', 'n_total', ...])
    
    return results
```

### Step 4: Generate .tex Content

After analysis, generate appropriate LaTeX:

```latex
\section{Stage Name Results}
\label{sec:results_stageN}

%Brief description of what was done

\begin{table}[htbp]
    \centering
    \caption{Summary caption}
    \label{tab:stageN_summary}
    \begin{tabular}{lccc}
        \toprule
        \textbf{Column 1} & \textbf{Column 2} & \textbf{Column 3} \\
        \midrule
        % ... values from aggregation
        \bottomrule
    \end{tabular}
\end{table}

\subsection{Key Findings}
\begin{itemize}
    \item Finding 1: {value}
    \item Finding 2: {value}
\end{itemize}

% Include relevant figure
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.9\textwidth]{../output/stageN_*/figures/filename.png}
    \caption{Figure caption}
    \label{fig:stageN_figure}
\end{figure}
```

---

## Important Rules

### DO:
1. ✅ Always create a dynamic analysis script first
2. ✅ Run the script to get actual values
3. ✅ Use ONLY real values from JSON in the document
4. ✅ Check figure filenames with `ls output/stageN_*/figures/`
5. ✅ Update NEW_SESSION.md after completing a stage

### DON'T:
1. ❌ Never fabricate numbers
2. ❌ Don't assume JSON structure - always explore first
3. ❌ Don't hardcode analyzers for specific stages
4. ❌ Don't skip validation (compile the document)

---

## Quick Commands

```bash
# List all stages with data
ls output/

# List metrics files for a stage
ls output/stage5_segmentation/metrics/

# List figures for a stage
ls output/stage5_segmentation/figures/

# Compile document
cd tex && make
```

---

## Example: Updating for Stage N

User: "Update document with Stage 5 results"

1. Create script:
```python
# analyze_stage5_temp.py
import json
from pathlib import Path

# Load and explore structure
data = json.load(open("output/stage5_segmentation/metrics/segmentation_metrics.json"))
print(json.dumps(data, indent=2)[:2000])  # First 2000 chars
```

2. Run to understand structure
3. Extract metrics
4. Write to .tex
5. Compile and validate
