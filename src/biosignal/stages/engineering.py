"""Stage 7: Feature Engineering.

Enriches the Stage 6 feature matrix with:
  - Protocol phase labels (baseline / stimulation / recovery)
  - EEG band power ratios
  - Baseline-normalised features (z-score relative to baseline windows)
  - Delta (Δ) and delta² (Δ²) temporal derivatives
  - Temporal aggregations (mean/std/min/max per subject/channel/phase)
  - Feature redundancy analysis (pairwise Pearson r)
  - Phase discriminability (one-way ANOVA F-statistic per feature)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from biosignal.config import (
    STAGE6_DATA_DIR,
    STAGE7_DATA_DIR,
    STAGE7_FIGURES_DIR,
    STAGE7_METRICS_DIR,
)

ACTIVE_MODALITIES = ["eeg", "ecg", "emg"]

META_COLS = {"subject_id", "modality", "window_id", "channel", "start_s", "end_s", "phase"}

# Features for which delta/delta2 are computed (to avoid column explosion)
DELTA_FEATURES = {
    "eeg": ["rms", "alpha_power", "beta_power", "hjorth_mobility", "spectral_entropy"],
    "ecg": ["rms", "mean_rr", "sdnn", "lf_hf_ratio", "hjorth_mobility"],
    "emg": ["rms", "mav", "mean_freq", "median_freq", "hjorth_mobility"],
}

EPS = 1e-12


# ---------------------------------------------------------------------------
# Phase assignment
# ---------------------------------------------------------------------------

def assign_phase(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'phase' column based on window start time."""
    conditions = [
        df["start_s"] < 30,
        (df["start_s"] >= 30) & (df["start_s"] < 60),
        df["start_s"] >= 60,
    ]
    df = df.copy()
    df["phase"] = np.select(conditions, ["baseline", "stimulation", "recovery"], default="unknown")
    return df


# ---------------------------------------------------------------------------
# EEG band power ratios
# ---------------------------------------------------------------------------

def add_band_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Add 5 band power ratio columns to EEG dataframe."""
    df = df.copy()
    alpha = df["alpha_power"]
    beta = df["beta_power"]
    theta = df["theta_power"]
    delta = df["delta_power"]

    df["alpha_beta_ratio"] = alpha / (beta + EPS)
    df["theta_alpha_ratio"] = theta / (alpha + EPS)
    df["engagement_index"] = beta / (alpha + theta + EPS)
    df["delta_beta_ratio"] = delta / (beta + EPS)
    df["theta_beta_ratio"] = theta / (beta + EPS)
    return df


# ---------------------------------------------------------------------------
# Baseline normalisation
# ---------------------------------------------------------------------------

def add_baseline_norm(df: pd.DataFrame) -> pd.DataFrame:
    """Add baseline-normalised columns for each feature."""
    df = df.copy()
    feature_cols = [c for c in df.columns if c not in META_COLS]

    baseline_stats: dict[tuple, dict[str, float]] = {}

    for (sid, ch), grp in df[df["phase"] == "baseline"].groupby(["subject_id", "channel"]):
        baseline_stats[(sid, ch)] = {
            col: {"mean": float(grp[col].mean()), "std": float(grp[col].std())}
            for col in feature_cols
        }

    norm_rows = []
    for idx, row in df.iterrows():
        key = (row["subject_id"], row["channel"])
        bstats = baseline_stats.get(key, {})
        norm_vals = {}
        for col in feature_cols:
            if col in bstats and bstats[col]["std"] > EPS:
                norm_vals[f"{col}_norm"] = (row[col] - bstats[col]["mean"]) / bstats[col]["std"]
            else:
                norm_vals[f"{col}_norm"] = np.nan
        norm_rows.append(norm_vals)

    norm_df = pd.DataFrame(norm_rows, index=df.index)
    return pd.concat([df, norm_df], axis=1)


# ---------------------------------------------------------------------------
# Delta features
# ---------------------------------------------------------------------------

def add_delta_features(df: pd.DataFrame, modality: str) -> pd.DataFrame:
    """Add Δ and Δ² for selected features, computed within subject/channel."""
    df = df.copy()
    target_feats = DELTA_FEATURES.get(modality, [])
    # keep only those that exist in the dataframe
    target_feats = [f for f in target_feats if f in df.columns]

    delta_rows = {f"delta_{f}": pd.Series(np.nan, index=df.index) for f in target_feats}
    delta2_rows = {f"delta2_{f}": pd.Series(np.nan, index=df.index) for f in target_feats}

    for (sid, ch), grp in df.groupby(["subject_id", "channel"]):
        grp_sorted = grp.sort_values("window_id")
        for feat in target_feats:
            vals = grp_sorted[feat].values.astype(float)
            d1 = np.diff(vals, prepend=np.nan)
            d2 = np.diff(d1, prepend=np.nan)
            d1[0] = np.nan
            d2[:2] = np.nan
            delta_rows[f"delta_{feat}"].loc[grp_sorted.index] = d1
            delta2_rows[f"delta2_{feat}"].loc[grp_sorted.index] = d2

    for col, series in {**delta_rows, **delta2_rows}.items():
        df[col] = series

    return df


# ---------------------------------------------------------------------------
# Temporal aggregations
# ---------------------------------------------------------------------------

def build_aggregated(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate features per (subject_id, channel, phase)."""
    feature_cols = [c for c in df.columns if c not in META_COLS]
    records = []

    for (sid, ch, phase), grp in df.groupby(["subject_id", "channel", "phase"]):
        row: dict[str, Any] = {
            "subject_id": sid,
            "channel": ch,
            "phase": phase,
            "n_windows": len(grp),
        }
        for col in feature_cols:
            col_data = grp[col].dropna()
            if len(col_data) == 0:
                row[f"{col}_mean"] = np.nan
                row[f"{col}_std"] = np.nan
                row[f"{col}_min"] = np.nan
                row[f"{col}_max"] = np.nan
            else:
                row[f"{col}_mean"] = float(col_data.mean())
                row[f"{col}_std"] = float(col_data.std())
                row[f"{col}_min"] = float(col_data.min())
                row[f"{col}_max"] = float(col_data.max())
        records.append(row)

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Redundancy analysis
# ---------------------------------------------------------------------------

def compute_redundancy(df: pd.DataFrame, modality: str, threshold: float = 0.95) -> dict:
    """Compute pairwise Pearson correlation and flag redundant feature pairs."""
    feature_cols = [
        c for c in df.columns
        if c not in META_COLS and not c.endswith("_norm")
        and not c.startswith("delta_") and not c.startswith("delta2_")
    ]
    corr = df[feature_cols].dropna().corr()

    redundant_pairs = []
    for i, f1 in enumerate(feature_cols):
        for f2 in feature_cols[i + 1:]:
            r = corr.loc[f1, f2]
            if abs(r) >= threshold:
                redundant_pairs.append({"feature_a": f1, "feature_b": f2, "r": round(float(r), 4)})

    return {
        "modality": modality,
        "n_features": len(feature_cols),
        "n_redundant_pairs": len(redundant_pairs),
        "threshold": threshold,
        "redundant_pairs": redundant_pairs,
        "correlation_matrix": corr.round(4).to_dict(),
    }


# ---------------------------------------------------------------------------
# Phase discriminability (one-way ANOVA per feature)
# ---------------------------------------------------------------------------

def compute_discriminability(df: pd.DataFrame, modality: str) -> dict:
    """One-way ANOVA across phases for each feature."""
    feature_cols = [
        c for c in df.columns
        if c not in META_COLS and not c.endswith("_norm")
        and not c.startswith("delta_") and not c.startswith("delta2_")
    ]
    results = []
    phases = ["baseline", "stimulation", "recovery"]

    for feat in feature_cols:
        groups = [df[df["phase"] == p][feat].dropna().values for p in phases]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            f_stat, p_val = stats.f_oneway(*groups)
        results.append({
            "feature": feat,
            "f_statistic": round(float(f_stat), 4) if np.isfinite(f_stat) else None,
            "p_value": round(float(p_val), 6) if np.isfinite(p_val) else None,
            "significant": bool(p_val < 0.05) if np.isfinite(p_val) else False,
        })

    results.sort(key=lambda x: x["f_statistic"] or 0, reverse=True)
    return {"modality": modality, "features": results}


# ---------------------------------------------------------------------------
# Visualisations
# ---------------------------------------------------------------------------

def _plot_redundancy_heatmap(corr_dict: dict, modality: str, out_dir: Path) -> None:
    feature_cols = list(corr_dict.keys())
    n = len(feature_cols)
    corr_arr = np.array([[corr_dict[f1].get(f2, 0.0) for f2 in feature_cols] for f1 in feature_cols])

    # Lower triangle only (mask upper triangle including diagonal)
    mask = np.triu(np.ones((n, n), dtype=bool))
    corr_masked = np.where(mask, np.nan, corr_arr)

    fig, ax = plt.subplots(figsize=(max(8, n * 0.9), max(6, n * 0.8)))
    im = ax.imshow(corr_masked, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(feature_cols, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(feature_cols, fontsize=8)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Correlation Coefficient")

    # Text annotations on lower triangle including diagonal
    for i in range(n):
        for j in range(i + 1):
            val = corr_arr[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7)

    ax.set_title(f"Feature Redundancy — {modality.upper()}\n(Pearson r, lower triangle)", fontsize=11)
    ax.set_xlabel("Feature")
    ax.set_ylabel("Feature")
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.savefig(out_dir / f"feature_redundancy_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_band_ratios(all_dfs: list[pd.DataFrame], out_dir: Path) -> None:
    ratio_cols = ["alpha_beta_ratio", "theta_alpha_ratio", "engagement_index",
                  "delta_beta_ratio", "theta_beta_ratio"]
    combined = pd.concat(all_dfs, ignore_index=True)
    available = [c for c in ratio_cols if c in combined.columns]
    if not available:
        return

    fig, axes = plt.subplots(1, len(available), figsize=(len(available) * 3.5, 5))
    if len(available) == 1:
        axes = [axes]
    colors = {"baseline": "#2196F3", "stimulation": "#F44336", "recovery": "#4CAF50"}

    for ax, col in zip(axes, available):
        for phase, color in colors.items():
            data = combined[combined["phase"] == phase][col].dropna()
            ax.boxplot(data, positions=[list(colors.keys()).index(phase)],
                       patch_artist=True, boxprops=dict(facecolor=color, alpha=0.7),
                       widths=0.6, showfliers=False)
        ax.set_title(col.replace("_", "\n"), fontsize=8)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["base", "stim", "rec"], fontsize=7)

    fig.suptitle("EEG Band Power Ratios by Protocol Phase", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir / "band_ratios_eeg.png", dpi=120)
    plt.close(fig)


def _plot_phase_discriminability(disc_results: dict[str, dict], out_dir: Path) -> None:
    fig, axes = plt.subplots(1, len(disc_results), figsize=(len(disc_results) * 5, 6))
    if len(disc_results) == 1:
        axes = [axes]

    for ax, (modality, disc) in zip(axes, disc_results.items()):
        features_data = disc.get("features", [])[:20]  # top 20
        if not features_data:
            continue
        names = [d["feature"] for d in features_data]
        fstats = [d["f_statistic"] or 0 for d in features_data]
        colors = ["#E53935" if d["significant"] else "#90A4AE" for d in features_data]
        y = range(len(names))
        ax.barh(list(y), fstats, color=colors, alpha=0.8)
        ax.set_yticks(list(y))
        ax.set_yticklabels(names, fontsize=7)
        ax.set_xlabel("F-statistic (ANOVA)")
        ax.set_title(f"Phase Discriminability — {modality.upper()}", fontsize=9)
        ax.invert_yaxis()

    fig.tight_layout()
    fig.savefig(out_dir / "phase_discriminability.png", dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(subject_id: int | None = None, verbose: bool = False) -> None:
    for d in [STAGE7_DATA_DIR, STAGE7_METRICS_DIR, STAGE7_FIGURES_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    subjects = [subject_id] if subject_id is not None else list(range(16))

    all_subject_metrics: dict[int, Any] = {}
    eeg_eng_dfs: list[pd.DataFrame] = []
    disc_results: dict[str, Any] = {}

    for sid in subjects:
        if verbose:
            print(f"[Stage 7] Processing subject s{sid:03d}...")

        subject_metrics: dict[str, Any] = {"subject_id": sid, "modalities": {}}

        for modality in ACTIVE_MODALITIES:
            src = STAGE6_DATA_DIR / f"s{sid:03d}_{modality}_features.csv"
            if not src.exists():
                if verbose:
                    print(f"  [{modality}] No Stage 6 CSV found, skipping.")
                continue

            df = pd.read_csv(src)
            if df.empty:
                continue

            n_original_cols = len(df.columns)

            # 1. Phase assignment
            df = assign_phase(df)

            # 2. Band ratios (EEG only)
            if modality == "eeg":
                df = add_band_ratios(df)

            # 3. Baseline normalisation
            df = add_baseline_norm(df)

            # 4. Delta features
            df = add_delta_features(df, modality)

            # Save engineered CSV
            eng_path = STAGE7_DATA_DIR / f"s{sid:03d}_{modality}_engineered.csv"
            df.to_csv(eng_path, index=False)

            # 5. Temporal aggregations
            agg_df = build_aggregated(df)
            agg_path = STAGE7_DATA_DIR / f"s{sid:03d}_{modality}_aggregated.csv"
            agg_df.to_csv(agg_path, index=False)

            n_new_cols = len(df.columns) - n_original_cols

            subject_metrics["modalities"][modality] = {
                "n_rows": len(df),
                "n_original_features": n_original_cols - 6,  # minus meta cols
                "n_engineered_cols": n_new_cols,
                "total_cols": len(df.columns),
                "phase_counts": df["phase"].value_counts().to_dict(),
            }

            if modality == "eeg":
                eeg_eng_dfs.append(df)

            if verbose:
                print(f"  [{modality}] {len(df)} rows, +{n_new_cols} new cols → {eng_path.name}")

        per_subj_path = STAGE7_METRICS_DIR / f"s{sid:03d}_engineering.json"
        with open(per_subj_path, "w") as f:
            json.dump(subject_metrics, f, indent=2)

        all_subject_metrics[sid] = subject_metrics

    # -----------------------------------------------------------------------
    # Global analyses — redundancy and discriminability (across all subjects)
    # -----------------------------------------------------------------------
    if verbose:
        print("[Stage 7] Computing redundancy and discriminability...")

    redundancy_all: dict[str, Any] = {}
    disc_all: dict[str, Any] = {}

    for modality in ACTIVE_MODALITIES:
        eng_files = sorted(STAGE7_DATA_DIR.glob(f"s*_{modality}_engineered.csv"))
        if not eng_files:
            continue
        try:
            combined = pd.concat([pd.read_csv(f) for f in eng_files], ignore_index=True)
            redundancy_all[modality] = compute_redundancy(combined, modality)
            disc_all[modality] = compute_discriminability(combined, modality)
        except Exception as e:
            if verbose:
                print(f"  [analysis] {modality} error: {e}")

    with open(STAGE7_METRICS_DIR / "redundancy_report.json", "w") as f:
        # omit full correlation matrix from report to keep file small
        slim = {
            m: {k: v for k, v in data.items() if k != "correlation_matrix"}
            for m, data in redundancy_all.items()
        }
        json.dump(slim, f, indent=2)

    with open(STAGE7_METRICS_DIR / "discriminability_report.json", "w") as f:
        json.dump(disc_all, f, indent=2)

    # -----------------------------------------------------------------------
    # Figures
    # -----------------------------------------------------------------------
    if verbose:
        print("[Stage 7] Generating figures...")

    for modality, red_data in redundancy_all.items():
        corr_dict = red_data.get("correlation_matrix", {})
        if corr_dict:
            try:
                _plot_redundancy_heatmap(corr_dict, modality, STAGE7_FIGURES_DIR)
            except Exception as e:
                if verbose:
                    print(f"  [plot] redundancy {modality}: {e}")

    if eeg_eng_dfs:
        try:
            _plot_band_ratios(eeg_eng_dfs, STAGE7_FIGURES_DIR)
        except Exception as e:
            if verbose:
                print(f"  [plot] band ratios: {e}")

    if disc_all:
        try:
            _plot_phase_discriminability(disc_all, STAGE7_FIGURES_DIR)
        except Exception as e:
            if verbose:
                print(f"  [plot] discriminability: {e}")

    # -----------------------------------------------------------------------
    # Global summary
    # -----------------------------------------------------------------------
    total_engineered_rows = sum(
        mod_data.get("n_rows", 0)
        for sid_m in all_subject_metrics.values()
        for mod_data in sid_m.get("modalities", {}).values()
    )

    global_summary = {
        "total_subjects_processed": len(all_subject_metrics),
        "total_engineered_rows": total_engineered_rows,
        "redundancy_summary": {
            m: {
                "n_features": redundancy_all[m]["n_features"],
                "n_redundant_pairs": redundancy_all[m]["n_redundant_pairs"],
            }
            for m in redundancy_all
        },
        "top_discriminating_features": {
            m: disc_all[m]["features"][:5] if disc_all.get(m) else []
            for m in ACTIVE_MODALITIES
        },
    }

    with open(STAGE7_METRICS_DIR / "engineering_metrics.json", "w") as f:
        json.dump(
            {"subjects": {str(k): v for k, v in all_subject_metrics.items()},
             "global_summary": global_summary},
            f, indent=2,
        )

    if verbose:
        print(f"[Stage 7] Done. {total_engineered_rows} engineered rows across {len(all_subject_metrics)} subjects.")
