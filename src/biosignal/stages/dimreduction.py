"""Stage 8: Dimensionality Reduction via PCA.

Reads per-(subject, channel, phase) aggregated feature matrices from Stage 7,
applies StandardScaler + PCA, saves reduced data and visualisations.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from biosignal.config import (
    STAGE7_DATA_DIR,
    STAGE8_DATA_DIR,
    STAGE8_FIGURES_DIR,
    STAGE8_METRICS_DIR,
)

warnings.filterwarnings("ignore", category=RuntimeWarning)

MODALITIES = ["eeg", "ecg", "emg"]
META_COLS = {"subject_id", "channel", "phase", "n_windows"}
NAN_DROP_THRESHOLD = 0.50  # drop feature columns with > 50% NaN


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_modality(modality: str) -> pd.DataFrame:
    """Concatenate all subject aggregated CSVs for a modality."""
    files = sorted(STAGE7_DATA_DIR.glob(f"s*_{modality}_aggregated.csv"))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_csv(f) for f in files]
    return pd.concat(dfs, ignore_index=True)


# ---------------------------------------------------------------------------
# PCA helpers
# ---------------------------------------------------------------------------

def _prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str], pd.DataFrame]:
    """Return (X_scaled, feature_names, meta_df) after cleaning and scaling."""
    meta_cols = [c for c in META_COLS if c in df.columns]
    meta_df = df[meta_cols].copy()

    feat_cols = [c for c in df.columns if c not in META_COLS]

    # Drop columns with too many NaN
    nan_frac = df[feat_cols].isna().mean()
    keep = nan_frac[nan_frac <= NAN_DROP_THRESHOLD].index.tolist()
    dropped = [c for c in feat_cols if c not in keep]

    X = df[keep].copy()
    # Impute remaining NaN with column median
    for col in X.columns:
        if X[col].isna().any():
            X[col] = X[col].fillna(X[col].median())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, keep, meta_df, dropped


def _run_pca(X: np.ndarray) -> tuple[PCA, np.ndarray, int, int]:
    """Fit full PCA; return (pca, X_transformed, n90, n95)."""
    n_components = min(X.shape[0], X.shape[1])
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X)

    cum_var = np.cumsum(pca.explained_variance_ratio_)
    n90 = int(np.searchsorted(cum_var, 0.90)) + 1
    n95 = int(np.searchsorted(cum_var, 0.95)) + 1
    return pca, X_pca, n90, n95


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _plot_scree(pca: PCA, modality: str, n90: int, n95: int) -> None:
    evr = pca.explained_variance_ratio_[:20]
    n_show = len(evr)
    x = np.arange(1, n_show + 1)

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(x, evr * 100, color="#4C72B0", edgecolor="white", linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Componente Principal", fontsize=11)
    ax.set_ylabel("Variância Explicada (%)", fontsize=11)
    ax.set_title(f"Diagrama de Cotovelo — {modality.upper()}", fontsize=12)
    ax.set_xticks(x)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    # Annotate n90 and n95 thresholds
    for nk, label, col in [(n90, "90%", "#e74c3c"), (n95, "95%", "#e67e22")]:
        if nk <= n_show:
            ax.axvline(nk + 0.5, color=col, linestyle="--", linewidth=1.2,
                       label=f"{label} variância acumulada (PC{nk})")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(fontsize=9, frameon=False)

    fig.tight_layout()
    fig.savefig(STAGE8_FIGURES_DIR / f"scree_plot_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_cumvar(pca: PCA, modality: str, n90: int, n95: int) -> None:
    cum_var = np.cumsum(pca.explained_variance_ratio_) * 100
    n_show = min(len(cum_var), 40)
    x = np.arange(1, n_show + 1)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, cum_var[:n_show], color="#4C72B0", linewidth=2, marker="o",
            markersize=3)
    ax.axhline(90, color="#e74c3c", linestyle="--", linewidth=1.2,
               label=f"90% (PC{n90})")
    ax.axhline(95, color="#e67e22", linestyle="--", linewidth=1.2,
               label=f"95% (PC{n95})")
    for nk, col in [(n90, "#e74c3c"), (n95, "#e67e22")]:
        if nk <= n_show:
            ax.axvline(nk, color=col, linestyle=":", linewidth=1.0, alpha=0.7)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Número de Componentes", fontsize=11)
    ax.set_ylabel("Variância Acumulada (%)", fontsize=11)
    ax.set_title(f"Variância Acumulada — {modality.upper()}", fontsize=12)
    ax.set_ylim(0, 105)
    ax.set_xticks(x[::2])
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9, frameon=False)

    fig.tight_layout()
    fig.savefig(STAGE8_FIGURES_DIR / f"cumulative_variance_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_scatter(X_pca: np.ndarray, meta_df: pd.DataFrame, modality: str) -> None:
    phase_colors = {"baseline": "#2ecc71", "stimulation": "#e74c3c", "recovery": "#3498db"}
    phases = meta_df["phase"].values if "phase" in meta_df.columns else np.full(len(X_pca), "unknown")

    fig, ax = plt.subplots(figsize=(7, 5))
    unique_phases = sorted(set(phases))
    for ph in unique_phases:
        mask = phases == ph
        color = phase_colors.get(ph, "#95a5a6")
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1], c=color, label=ph.capitalize(),
                   alpha=0.6, s=25, edgecolors="none")

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("PC1", fontsize=11)
    ax.set_ylabel("PC2", fontsize=11)
    ax.set_title(f"Dispersão PCA (PC1 × PC2) — {modality.upper()}", fontsize=12)
    ax.tick_params(length=0)
    ax.legend(fontsize=9, frameon=False)

    fig.tight_layout()
    fig.savefig(STAGE8_FIGURES_DIR / f"pca_scatter_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_loadings(pca: PCA, feature_names: list[str], modality: str, n_pcs: int = 5) -> None:
    n_pcs = min(n_pcs, pca.n_components_)
    loadings = pca.components_[:n_pcs]  # (n_pcs, n_features)

    # Select top 15 features by max absolute loading across shown PCs
    max_abs = np.abs(loadings).max(axis=0)
    top_idx = np.argsort(max_abs)[::-1][:15]
    top_features = [feature_names[i] for i in top_idx]
    L = loadings[:, top_idx]  # (n_pcs, 15)

    fig, ax = plt.subplots(figsize=(10, 4))
    vmax = np.abs(L).max()
    im = ax.imshow(L, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(top_features)))
    ax.set_xticklabels(top_features, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(n_pcs))
    ax.set_yticklabels([f"PC{i+1}" for i in range(n_pcs)], fontsize=9)

    for i in range(n_pcs):
        for j in range(len(top_features)):
            val = L[i, j]
            color = "white" if abs(val) > vmax * 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=6)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"Cargas PCA (top 15 atributos) — {modality.upper()}", fontsize=12)
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)

    fig.tight_layout()
    fig.savefig(STAGE8_FIGURES_DIR / f"pca_loadings_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(subject_id: Optional[int] = None, verbose: bool = False) -> None:
    STAGE8_DATA_DIR.mkdir(parents=True, exist_ok=True)
    STAGE8_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    STAGE8_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    global_metrics: dict = {}

    for modality in MODALITIES:
        if verbose:
            print(f"\n[Stage 8] {modality.upper()} — loading aggregated data...")

        df = _load_modality(modality)
        if df.empty:
            if verbose:
                print(f"  No data found for {modality}, skipping.")
            continue

        n_samples = len(df)
        X_scaled, feat_cols, meta_df, dropped_cols = _prepare_features(df)
        n_features_input = len(feat_cols)
        n_features_dropped = len(dropped_cols)

        if verbose:
            print(f"  {n_samples} observations, {n_features_input} features "
                  f"({n_features_dropped} dropped for NaN)")

        pca, X_pca, n90, n95 = _run_pca(X_scaled)
        evr = pca.explained_variance_ratio_.tolist()
        cum_var = np.cumsum(evr).tolist()

        if verbose:
            print(f"  n_components_90={n90}, n_components_95={n95} "
                  f"(of {pca.n_components_} total)")

        # --- Save reduced data (95% threshold) ---
        pc_cols = [f"PC{i+1}" for i in range(n95)]
        reduced_df = meta_df.copy()
        reduced_df[pc_cols] = X_pca[:, :n95]
        reduced_df.to_csv(STAGE8_DATA_DIR / f"{modality}_pca_reduced.csv", index=False)

        # --- Save loadings ---
        loadings_df = pd.DataFrame(
            pca.components_[:n95].T,
            index=feat_cols,
            columns=pc_cols,
        )
        loadings_df.index.name = "feature"
        loadings_df.to_csv(STAGE8_DATA_DIR / f"{modality}_pca_loadings.csv")

        # --- Metrics ---
        mod_metrics = {
            "modality": modality,
            "n_samples": n_samples,
            "n_features_input": n_features_input,
            "n_features_dropped": n_features_dropped,
            "dropped_features": dropped_cols,
            "n_components_total": pca.n_components_,
            "n_components_90": n90,
            "n_components_95": n95,
            "explained_variance_ratio": evr,
            "cumulative_variance": cum_var,
            "variance_retained_90": float(np.sum(evr[:n90])),
            "variance_retained_95": float(np.sum(evr[:n95])),
        }
        with open(STAGE8_METRICS_DIR / f"{modality}_pca_metrics.json", "w") as f:
            json.dump(mod_metrics, f, indent=2)

        global_metrics[modality] = mod_metrics

        # --- Figures ---
        _plot_scree(pca, modality, n90, n95)
        _plot_cumvar(pca, modality, n90, n95)
        _plot_scatter(X_pca, meta_df, modality)
        _plot_loadings(pca, feat_cols, modality)

        if verbose:
            print(f"  Figures saved.")

    # --- Global summary ---
    with open(STAGE8_METRICS_DIR / "dimreduction_metrics.json", "w") as f:
        json.dump(global_metrics, f, indent=2)

    if verbose:
        print(f"\n[Stage 8] Complete. Output → {STAGE8_DATA_DIR}")
