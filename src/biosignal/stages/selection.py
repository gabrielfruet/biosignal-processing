"""Stage 9: Feature Selection via Filter, Wrapper, and Embedded methods on PCA components."""

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
from sklearn.feature_selection import f_classif, mutual_info_classif, RFECV
from sklearn.svm import LinearSVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold

from biosignal.config import (
    STAGE8_DATA_DIR,
    STAGE9_DATA_DIR,
    STAGE9_FIGURES_DIR,
    STAGE9_METRICS_DIR,
)

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

MODALITIES = ["eeg", "ecg", "emg"]
ALPHA = 0.05
N_CV_FOLDS = 5
RNG = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode_phase(y_str: pd.Series) -> np.ndarray:
    le = LabelEncoder()
    return le.fit_transform(y_str)


def _cohen_f2(f_stat: float, n: int, k: int = 3) -> float:
    """Cohen's f² effect size for one-way ANOVA."""
    denom = n - k
    if denom <= 0 or f_stat <= 0:
        return 0.0
    return float(f_stat * (k - 1) / denom)


def _bonferroni(p_values: np.ndarray) -> np.ndarray:
    return np.minimum(p_values * len(p_values), 1.0)


# ---------------------------------------------------------------------------
# Selection methods
# ---------------------------------------------------------------------------

def _filter_methods(X: np.ndarray, y: np.ndarray, feat_names: list[str]) -> pd.DataFrame:
    n, k = X.shape[0], 3
    f_stats, p_vals = f_classif(X, y)
    mi_scores = mutual_info_classif(X, y, random_state=RNG)
    p_bonf = _bonferroni(p_vals)
    f2 = np.array([_cohen_f2(f, n, k) for f in f_stats])

    df = pd.DataFrame({
        "feature": feat_names,
        "anova_f": f_stats,
        "anova_p": p_vals,
        "anova_p_bonf": p_bonf,
        "anova_sig_bonf": p_bonf < ALPHA,
        "mi": mi_scores,
        "cohens_f2": f2,
    })
    return df


def _rfe_wrapper(X: np.ndarray, y: np.ndarray) -> tuple[int, np.ndarray, np.ndarray]:
    """Returns (n_optimal, ranking_array, cv_scores_array)."""
    min_features = max(1, X.shape[1] // 4)
    estimator = LinearSVC(penalty="l2", max_iter=5000, random_state=RNG)
    cv = StratifiedKFold(n_splits=min(N_CV_FOLDS, int(np.bincount(y).min())), shuffle=True, random_state=RNG)
    rfecv = RFECV(estimator=estimator, step=1, cv=cv, scoring="accuracy",
                  min_features_to_select=min_features, n_jobs=-1)
    rfecv.fit(X, y)
    # rfecv.cv_results_["mean_test_score"] in newer sklearn
    try:
        cv_scores = rfecv.cv_results_["mean_test_score"]
    except (AttributeError, KeyError):
        cv_scores = np.array(rfecv.grid_scores_) if hasattr(rfecv, "grid_scores_") else np.zeros(X.shape[1])
    return int(rfecv.n_features_), rfecv.ranking_, cv_scores


def _l1_embedded(X: np.ndarray, y: np.ndarray, feat_names: list[str]) -> pd.DataFrame:
    clf = LinearSVC(penalty="l1", dual=False, max_iter=5000, C=0.1, random_state=RNG)
    clf.fit(X, y)
    coef_max = np.abs(clf.coef_).max(axis=0)
    return pd.DataFrame({"feature": feat_names, "coef_max": coef_max,
                         "l1_selected": coef_max > 0})


# ---------------------------------------------------------------------------
# Consensus ranking
# ---------------------------------------------------------------------------

def _consensus(filter_df: pd.DataFrame, rfe_ranking: np.ndarray,
               l1_df: pd.DataFrame) -> pd.DataFrame:
    n = len(filter_df)
    df = filter_df.copy()

    # rank by ANOVA F descending
    df["anova_rank"] = df["anova_f"].rank(ascending=False)
    # rank by MI descending
    df["mi_rank"] = df["mi"].rank(ascending=False)
    # L1 coef rank
    df["coef_max"] = l1_df["coef_max"].values
    df["l1_selected"] = l1_df["l1_selected"].values
    df["coef_rank"] = df["coef_max"].rank(ascending=False)
    # RFE ranking (1 = best in sklearn)
    df["rfe_rank"] = rfe_ranking.astype(float)

    df["consensus_rank"] = (df["anova_rank"] + df["mi_rank"] + df["coef_rank"]) / 3.0
    df = df.sort_values("consensus_rank").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _plot_anova(df: pd.DataFrame, modality: str, n_sig: int) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#e74c3c" if sig else "#4C72B0" for sig in df["anova_sig_bonf"]]
    x = np.arange(len(df))
    ax.bar(x, df["anova_f"], color=colors, edgecolor="none")
    ax.set_xticks(x[::max(1, len(x)//15)])
    ax.set_xticklabels(df["feature"].iloc[::max(1, len(x)//15)], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("F-estatística ANOVA", fontsize=10)
    ax.set_title(f"ANOVA F-score por Componente — {modality.upper()} "
                 f"({n_sig} significativos, Bonferroni)", fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor="#e74c3c", label="Significativo (Bonferroni)"),
                       Patch(facecolor="#4C72B0", label="Não significativo")]
    ax.legend(handles=legend_elements, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(STAGE9_FIGURES_DIR / f"anova_fscores_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_mi(df: pd.DataFrame, modality: str) -> None:
    df_sorted = df.sort_values("mi", ascending=False).head(20)
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(df_sorted))
    ax.bar(x, df_sorted["mi"], color="#2ecc71", edgecolor="none")
    ax.set_xticks(x)
    ax.set_xticklabels(df_sorted["feature"], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Informação Mútua", fontsize=10)
    ax.set_title(f"Top 20 componentes por Informação Mútua — {modality.upper()}", fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(STAGE9_FIGURES_DIR / f"mi_scores_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_rfe(cv_scores: np.ndarray, n_optimal: int, modality: str) -> None:
    x = np.arange(1, len(cv_scores) + 1)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, cv_scores * 100, color="#4C72B0", linewidth=2, marker="o", markersize=3)
    ax.axvline(n_optimal, color="#e74c3c", linestyle="--", linewidth=1.5,
               label=f"Ótimo: {n_optimal} atributos")
    ax.set_xlabel("Número de componentes", fontsize=10)
    ax.set_ylabel("Acurácia CV (%)", fontsize=10)
    ax.set_title(f"Curva RFECV — {modality.upper()}", fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(STAGE9_FIGURES_DIR / f"rfe_cv_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_consensus(df: pd.DataFrame, modality: str) -> None:
    top = df.head(min(15, len(df)))
    methods = ["anova_rank", "mi_rank", "coef_rank", "rfe_rank"]
    labels = ["ANOVA", "MI", "L1-coef", "RFE"]
    data = top[methods].values.T  # (4, n_feats)

    fig, ax = plt.subplots(figsize=(10, 4))
    vmax = data.max()
    im = ax.imshow(data, cmap="YlOrRd_r", vmin=1, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top["feature"], rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(4))
    ax.set_yticklabels(labels, fontsize=9)
    for i in range(4):
        for j in range(len(top)):
            val = data[i, j]
            color = "white" if val < vmax * 0.4 else "black"
            ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=6, color=color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(f"Ranking por método (top {len(top)} componentes) — {modality.upper()}", fontsize=11)
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02, label="Posição no ranking")
    fig.tight_layout()
    fig.savefig(STAGE9_FIGURES_DIR / f"consensus_ranking_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(subject_id: Optional[int] = None, verbose: bool = False) -> None:
    STAGE9_DATA_DIR.mkdir(parents=True, exist_ok=True)
    STAGE9_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    STAGE9_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    global_metrics: dict = {}

    for modality in MODALITIES:
        src = STAGE8_DATA_DIR / f"{modality}_pca_reduced.csv"
        if not src.exists():
            if verbose:
                print(f"[Stage 9] {modality.upper()} — input not found, skipping.")
            continue

        df = pd.read_csv(src)
        pc_cols = [c for c in df.columns if c.startswith("PC")]
        if not pc_cols or "phase" not in df.columns:
            if verbose:
                print(f"[Stage 9] {modality.upper()} — no PC columns or phase, skipping.")
            continue

        X = df[pc_cols].values
        y = _encode_phase(df["phase"])
        n_input = len(pc_cols)

        if verbose:
            print(f"\n[Stage 9] {modality.upper()} — {X.shape[0]} obs × {n_input} PCs")

        # --- Filter ---
        filter_df = _filter_methods(X, y, pc_cols)
        n_sig_bonf = int(filter_df["anova_sig_bonf"].sum())
        if verbose:
            print(f"  ANOVA: {n_sig_bonf}/{n_input} significant (Bonferroni)")

        # --- RFE ---
        try:
            n_rfe, rfe_ranking, cv_scores = _rfe_wrapper(X, y)
        except Exception as e:
            if verbose:
                print(f"  RFE failed ({e}), using n_rfe=n_sig_bonf or 1")
            n_rfe = max(1, n_sig_bonf)
            rfe_ranking = np.arange(1, n_input + 1)
            cv_scores = np.zeros(n_input)

        best_cv = float(cv_scores.max()) if len(cv_scores) > 0 else 0.0
        if verbose:
            print(f"  RFE: optimal {n_rfe} features, best CV acc={best_cv:.3f}")

        # --- L1 ---
        l1_df = _l1_embedded(X, y, pc_cols)
        n_l1 = int(l1_df["l1_selected"].sum())
        if verbose:
            print(f"  L1: {n_l1}/{n_input} non-zero features")

        # --- Consensus ---
        consensus_df = _consensus(filter_df, rfe_ranking, l1_df)
        n_consensus = int(n_rfe)

        # --- Save selected CSV ---
        selected_pcs = consensus_df.head(n_consensus)["feature"].tolist()
        meta_cols = [c for c in ["subject_id", "channel", "phase", "n_windows"] if c in df.columns]
        out_df = df[meta_cols + selected_pcs].copy()
        out_df.to_csv(STAGE9_DATA_DIR / f"{modality}_selected.csv", index=False)

        # --- Metrics ---
        ranking_records = consensus_df[[
            "feature", "anova_f", "anova_p", "anova_p_bonf", "anova_sig_bonf",
            "mi", "cohens_f2", "coef_max", "l1_selected", "rfe_rank", "consensus_rank"
        ]].to_dict(orient="records")
        # convert numpy types for JSON serialisation
        for rec in ranking_records:
            for k, v in rec.items():
                if hasattr(v, "item"):
                    rec[k] = v.item()

        mod_metrics = {
            "modality": modality,
            "n_pcs_input": n_input,
            "n_selected_anova_bonf": n_sig_bonf,
            "n_selected_rfe": n_rfe,
            "n_selected_l1": n_l1,
            "n_selected_consensus": n_consensus,
            "rfe_best_cv_accuracy": best_cv,
            "cv_scores": cv_scores.tolist(),
            "feature_ranking": ranking_records,
        }
        with open(STAGE9_METRICS_DIR / f"{modality}_selection.json", "w") as f:
            json.dump(mod_metrics, f, indent=2)

        global_metrics[modality] = {k: v for k, v in mod_metrics.items()
                                     if k != "feature_ranking"}

        # --- Figures ---
        _plot_anova(filter_df, modality, n_sig_bonf)
        _plot_mi(filter_df, modality)
        _plot_rfe(cv_scores, n_rfe, modality)
        _plot_consensus(consensus_df, modality)

        if verbose:
            print(f"  Consensus selected: {n_consensus} PCs → saved to {modality}_selected.csv")

    with open(STAGE9_METRICS_DIR / "selection_metrics.json", "w") as f:
        json.dump(global_metrics, f, indent=2)

    if verbose:
        print(f"\n[Stage 9] Complete. Output → {STAGE9_DATA_DIR}")
