#!/usr/bin/env python3
"""
Generic metrics explorer for biosignal pipeline stages.
This script dynamically explores JSON metrics and extracts key values.

Usage:
    python analyze_metrics.py <stage_number> [--explore]
    python analyze_metrics.py 5                    # Analyze stage 5
    python analyze_metrics.py 5 --explore          # Explore structure first
    python analyze_metrics.py all                  # List all available stages
"""

import json
import sys
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional


STAGE_NAMES = {
    1: "Acquisition",
    2: "SQI (Signal Quality Index)",
    3: "Statistics",
    4: "Cleaning",
    5: "Segmentation",
    6: "Feature Extraction",
    7: "Feature Engineering",
    8: "Dimensionality Reduction",
    9: "Feature Selection",
    10: "Validation",
}

STAGE_DIRS = {
    1: "stage1_acquisition",
    2: "stage2_sqi",
    3: "stage3_statistics",
    4: "stage4_cleaning",
    5: "stage5_segmentation",
    6: "stage6_features",
    7: "stage7_engineering",
    8: "stage8_dimreduction",
    9: "stage9_selection",
    10: "stage10_validation",
}


def find_metrics_dir(stage: int) -> Optional[Path]:
    """Find the metrics directory for a given stage."""
    # Direct path
    if stage in STAGE_DIRS:
        path = Path(f"output/{STAGE_DIRS[stage]}/metrics")
        if path.exists():
            return path
    
    # Glob fallback
    for pattern in [f"output/stage{stage}_*/metrics", f"output/Stage{stage}*/metrics"]:
        dirs = glob.glob(pattern)
        if dirs:
            return Path(dirs[0])
    
    return None


def find_all_json_files(metrics_dir: Path) -> List[Path]:
    """Find all JSON files in metrics directory."""
    if not metrics_dir.exists():
        return []
    return sorted(metrics_dir.glob("*.json"))


def explore_structure(obj: Any, path: str = "", depth: int = 0, max_depth: int = 5) -> None:
    """Dynamically explore JSON structure."""
    if depth > max_depth:
        return
    
    indent = "  " * depth
    
    if isinstance(obj, dict):
        keys = list(obj.keys())
        print(f"{indent}{path}: dict with {len(keys)} keys")
        for key in keys[:15]:  # Limit keys shown
            explore_structure(obj[key], key, depth + 1, max_depth)
        if len(keys) > 15:
            print(f"{indent}  ... and {len(keys) - 15} more keys")
    
    elif isinstance(obj, list):
        if len(obj) == 0:
            print(f"{indent}{path}: empty list")
        elif isinstance(obj[0], dict):
            print(f"{indent}{path}: list[{len(obj)}] of dicts")
            if len(obj) > 0:
                explore_structure(obj[0], f"{path}[0]", depth + 1, max_depth)
        else:
            sample = str(obj[:3])[:50]
            print(f"{indent}{path}: list[{len(obj)}] = {sample}...")
    
    elif isinstance(obj, (int, float)):
        if isinstance(obj, float) and abs(obj) < 0.01:
            print(f"{indent}{path}: {obj:.2e}")
        else:
            print(f"{indent}{path}: {obj}")
    
    elif isinstance(obj, str):
        print(f"{indent}{path}: \"{obj[:30]}...\"" if len(obj) > 30 else f"{indent}{path}: \"{obj}\"")
    
    else:
        print(f"{indent}{path}: {type(obj).__name__}")


def extract_numbers_recursive(obj: Any) -> List[tuple]:
    """Recursively find all numeric values with their paths."""
    results = []
    
    def traverse(o, path_parts):
        if isinstance(o, dict):
            for key, val in o.items():
                traverse(val, path_parts + [key])
        elif isinstance(o, list):
            for i, val in enumerate(o[:20]):  # Limit list items
                traverse(val, path_parts + [f"[{i}]"])
        elif isinstance(o, (int, float)):
            results.append((".".join(path_parts), o))
    
    traverse(obj, [])
    return results


def find_nested_value(obj: Dict, keys: List[str]) -> Any:
    """Navigate nested dict by list of keys."""
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        else:
            return None
    return obj


def analyze_generic(data: Dict, stage: int) -> str:
    """Generic analysis based on stage number."""
    output = []
    output.append("=" * 60)
    output.append(f"STAGE {stage} ANALYSIS: {STAGE_NAMES.get(stage, 'Unknown')}")
    output.append("=" * 60)
    
    # Extract common patterns
    numbers = extract_numbers_recursive(data)
    
    # Categorize numbers
    windows = [(p, v) for p, v in numbers if 'window' in p.lower()]
    subjects = [(p, v) for p, v in numbers if 'subject' in p.lower() and v < 20]
    rates = [(p, v) for p, v in numbers if 'rate' in p.lower() or ('percent' in p.lower()) or ('%' in p)]
    samples = [(p, v) for p, v in numbers if 'sample' in p.lower()]
    duration = [(p, v) for p, v in numbers if 'duration' in p.lower() and v > 0]
    
    output.append(f"\nNumeric patterns found:")
    
    if windows:
        output.append(f"\n  Windows-related ({len(windows)} found):")
        for path, val in windows[:10]:
            output.append(f"    {path}: {val}")
    
    if subjects:
        output.append(f"\n  Subject-related ({len(subjects)} found):")
        for path, val in subjects[:5]:
            output.append(f"    {path}: {val}")
    
    if rates:
        output.append(f"\n  Rates/percentages ({len(rates)} found):")
        for path, val in rates[:10]:
            if isinstance(val, float):
                output.append(f"    {path}: {val:.2%}" if val <= 1 else f"    {path}: {val:.2f}%")
            else:
                output.append(f"    {path}: {val}")
    
    if samples:
        output.append(f"\n  Sample counts ({len(samples)} found):")
        for path, val in samples[:5]:
            output.append(f"    {path}: {val:,}")
    
    if duration:
        output.append(f"\n  Durations ({len(duration)} found):")
        for path, val in duration[:5]:
            output.append(f"    {path}: {val:.1f}s")
    
    # Show top-level keys
    if isinstance(data, dict):
        output.append(f"\nTop-level keys:")
        for key in list(data.keys())[:10]:
            val = data[key]
            if isinstance(val, dict):
                output.append(f"  {key}: dict ({len(val)} keys)")
            elif isinstance(val, list):
                output.append(f"  {key}: list[{len(val)}]")
            elif isinstance(val, (int, float)):
                output.append(f"  {key}: {val}")
            else:
                output.append(f"  {key}: {type(val).__name__}")
    
    output.append("\n" + "=" * 60)
    return "\n".join(output)


def main():
    if len(sys.argv) == 1 or sys.argv[1] == "--help" or sys.argv[1] == "-h":
        print("Biosignal Metrics Explorer")
        print("=" * 40)
        print("Usage: python analyze_metrics.py <stage> [options]")
        print()
        print("Options:")
        print("  --explore    Show JSON structure only")
        print("  --all        List all available stages")
        print()
        print("Examples:")
        print("  python analyze_metrics.py 5           # Analyze stage 5")
        print("  python analyze_metrics.py 5 --explore  # Explore structure")
        return
    
    if sys.argv[1] == "--all":
        print("Available stages:")
        for i in range(1, 11):
            path = find_metrics_dir(i)
            status = "✓" if path and path.exists() else "○"
            files = len(list(path.glob("*.json"))) if path and path.exists() else 0
            print(f"  {status} Stage {i}: {STAGE_NAMES.get(i, 'Unknown')} ({files} files)")
        return
    
    try:
        stage = int(sys.argv[1])
    except ValueError:
        print(f"Invalid stage: {sys.argv[1]}")
        return
    
    explore_only = "--explore" in sys.argv
    
    metrics_dir = find_metrics_dir(stage)
    
    if not metrics_dir:
        print(f"Stage {stage} not found. Available stages:")
        for i in range(1, 11):
            path = find_metrics_dir(i)
            if path and path.exists():
                print(f"  Stage {i}: {STAGE_NAMES.get(i, 'Unknown')}")
        return
    
    json_files = find_all_json_files(metrics_dir)
    
    if not json_files:
        print(f"No JSON files found in {metrics_dir}")
        return
    
    print(f"Found {len(json_files)} JSON file(s) in {metrics_dir}")
    print()
    
    # Load first file for analysis
    with open(json_files[0]) as f:
        data = json.load(f)
    
    if explore_only:
        explore_structure(data)
    else:
        print(analyze_generic(data, stage))
    
    print("\n" + "=" * 60)
    print("TIP: Use --explore to see the full JSON structure")
    print("     Then copy values for .tex document")


if __name__ == "__main__":
    main()
