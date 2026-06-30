"""Stage 10: Final Statistical Validation — VIF, separability, balance, dataset assembly."""

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
from scipy import stats
from sklearn.feature_selection import f_classif
from sklearn.preprocessing import LabelEncoder
from statsmodels.stats.outliers_influence import variance_inflation_factor

from biosignal.config import (
    STAGE9_DATA_DIR,
    STAGE10_DATA_DIR,
    STAGE10_FIGURES_DIR,
    STAGE10_METRICS_DIR,
)

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

MODALITIES = ["eeg", "ecg", "emg"]
VIF_WARN = 5.0
VIF_SEVERE = 10.0


# ---------------------------------------------------------------------------
# VAL-001: VIF
# ---------------------------------------------------------------------------

def _compute_vif(X: np.ndarray, feat_names: list[str]) -> pd.DataFrame:
    """Compute VIF for each feature. PCA components should be ~1 by construction."""
    if X.shape[1] <= 1:
        return pd.DataFrame({"feature": feat_names, "vif": [1.0] * len(feat_names)})
    records = []
    for i, name in enumerate(feat_names):
        try:
            vif = variance_inflation_factor(X, i)
        except Exception:
            vif = float("nan")
        records.append({"feature": name, "vif": float(vif)})
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# VAL-002: Separability
# ---------------------------------------------------------------------------

def _bhattacharyya(mu1, sigma1, mu2, sigma2) -> float:
    """Bhattacharyya distance between two 1D Gaussians."""
    sigma_avg = (sigma1 + sigma2) / 2
    if sigma_avg <= 0:
        return 0.0
    term1 = 0.25 * ((mu1 - mu2) ** 2) / sigma_avg
    term2 = 0.5 * np.log(sigma_avg / (np.sqrt(sigma1 * sigma2) + 1e-12))
    return float(term1 + term2)


def _separability_metrics(X: np.ndarray, y: np.ndarray,
                           feat_names: list[str]) -> dict:
    """ANOVA eta², Bhattacharyya distance (top 2 PCs), MANOVA Pillai."""
    phases = np.unique(y)
    n_feat = X.shape[1]

    # ANOVA per feature → η²
    f_stats, p_vals = f_classif(X, y)
    # η² = SS_between / SS_total approximation: F*(k-1) / (F*(k-1) + (n-k))
    k, n = len(phases), X.shape[0]
    eta2 = np.array([
        (f * (k - 1)) / (f * (k - 1) + (n - k)) if f > 0 else 0.0
        for f in f_stats
    ])
    top_pc_idx = int(np.argmax(f_stats))

    # Bhattacharyya on top PC
    bhat_pairs = {}
    for i, ph1 in enumerate(phases):
        for ph2 in phases[i + 1:]:
            x1 = X[y == ph1, top_pc_idx]
            x2 = X[y == ph2, top_pc_idx]
            bd = _bhattacharyya(x1.mean(), x1.var(), x2.mean(), x2.var())
            bhat_pairs[f"{ph1}_vs_{ph2}"] = round(bd, 4)

    # MANOVA via Pillai trace (manual: between/total scatter)
    try:
        grand_mean = X.mean(axis=0)
        S_B = np.zeros((n_feat, n_feat))
        S_W = np.zeros((n_feat, n_feat))
        for ph in phases:
            Xg = X[y == ph]
            ng = len(Xg)
            diff = Xg.mean(axis=0) - grand_mean
            S_B += ng * np.outer(diff, diff)
            S_W += np.cov(Xg.T, ddof=1) * (ng - 1) if ng > 1 else np.zeros((n_feat, n_feat))
        S_T = S_B + S_W
        # Pillai trace = tr(S_B @ inv(S_T))
        try:
            pillai = float(np.trace(S_B @ np.linalg.pinv(S_T)))
        except Exception:
            pillai = float("nan")
        # Approximate F for Pillai
        p_pillai = float("nan")
    except Exception:
        pillai = float("nan")
        p_pillai = float("nan")

    # Simple multivariate test: Wilks-like p-value via combined ANOVA
    combined_p = float(np.min(p_vals))

    return {
        "top_pc_by_f": feat_names[top_pc_idx],
        "top_pc_f": float(f_stats[top_pc_idx]),
        "top_pc_eta2": float(eta2[top_pc_idx]),
        "mean_eta2": float(eta2.mean()),
        "bhattacharyya_top_pc": bhat_pairs,
        "pillai_trace": round(pillai, 4) if not np.isnan(pillai) else None,
        "min_anova_p": combined_p,
        "separability_ok": bool(combined_p < 0.05),
    }


# ---------------------------------------------------------------------------
# VAL-003: Class balance
# ---------------------------------------------------------------------------

def _balance_metrics(y_str: pd.Series) -> dict:
    counts = y_str.value_counts().to_dict()
    counts = {str(k): int(v) for k, v in counts.items()}
    vals = list(counts.values())
    ratio = float(max(vals) / min(vals)) if min(vals) > 0 else float("inf")
    return {
        "counts": counts,
        "imbalance_ratio": round(ratio, 3),
        "balance_ok": ratio <= 1.5,
    }


# ---------------------------------------------------------------------------
# VAL-004: Density curves
# ---------------------------------------------------------------------------

def _plot_density(df: pd.DataFrame, pc_cols: list[str], modality: str) -> None:
    top_pcs = pc_cols[:min(3, len(pc_cols))]
    phase_colors = {"baseline": "#2ecc71", "stimulation": "#e74c3c", "recovery": "#3498db"}
    phases = sorted(df["phase"].unique())

    fig, axes = plt.subplots(1, len(top_pcs), figsize=(5 * len(top_pcs), 4))
    if len(top_pcs) == 1:
        axes = [axes]

    for ax, pc in zip(axes, top_pcs):
        for ph in phases:
            vals = df.loc[df["phase"] == ph, pc].dropna().values
            if len(vals) < 3:
                continue
            kde = stats.gaussian_kde(vals)
            x_range = np.linspace(vals.min() - 0.5, vals.max() + 0.5, 200)
            ax.plot(x_range, kde(x_range), color=phase_colors.get(ph, "#95a5a6"),
                    label=ph.capitalize(), linewidth=2)
            ax.fill_between(x_range, kde(x_range), alpha=0.12,
                            color=phase_colors.get(ph, "#95a5a6"))
        ax.set_title(pc, fontsize=10)
        ax.set_xlabel("Score", fontsize=9)
        ax.set_ylabel("Densidade" if ax == axes[0] else "", fontsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)

    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle(f"Curvas de Densidade por Fase — {modality.upper()}", fontsize=12)
    fig.tight_layout()
    fig.savefig(STAGE10_FIGURES_DIR / f"density_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_vif(vif_df: pd.DataFrame, modality: str) -> None:
    fig, ax = plt.subplots(figsize=(max(6, len(vif_df) * 0.4), 4))
    colors = ["#e74c3c" if v > VIF_WARN else "#4C72B0" for v in vif_df["vif"]]
    x = np.arange(len(vif_df))
    ax.bar(x, vif_df["vif"], color=colors, edgecolor="none")
    ax.axhline(VIF_WARN, color="#e74c3c", linestyle="--", linewidth=1,
               label=f"Limiar moderado (VIF={VIF_WARN:.0f})")
    ax.axhline(VIF_SEVERE, color="#c0392b", linestyle=":", linewidth=1,
               label=f"Limiar severo (VIF={VIF_SEVERE:.0f})")
    ax.set_xticks(x[::max(1, len(x) // 15)])
    ax.set_xticklabels(vif_df["feature"].iloc[::max(1, len(x) // 15)],
                       rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("VIF", fontsize=10)
    ax.set_title(f"Fator de Inflação da Variância (VIF) — {modality.upper()}", fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(STAGE10_FIGURES_DIR / f"vif_{modality}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_balance(balance: dict, modality: str) -> None:
    counts = balance["counts"]
    phases = list(counts.keys())
    vals = [counts[p] for p in phases]
    phase_colors = {"baseline": "#2ecc71", "stimulation": "#e74c3c", "recovery": "#3498db"}
    colors = [phase_colors.get(p, "#95a5a6") for p in phases]

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(phases, vals, color=colors, edgecolor="none")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(v), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Observações", fontsize=10)
    ax.set_title(f"Balanceamento de Classes — {modality.upper()}\n"
                 f"(razão={balance['imbalance_ratio']:.2f})", fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(STAGE10_FIGURES_DIR / f"class_balance_{modality}.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# VAL-005: Dataset final assembly
# ---------------------------------------------------------------------------

def _assemble_final(modal_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join EEG, ECG, EMG on (subject_id, phase), averaging across channels."""
    parts = []
    for mod, df in modal_dfs.items():
        pc_cols = [c for c in df.columns if c.startswith("PC")]
        meta = ["subject_id", "phase"]
        agg = df[meta + pc_cols].groupby(["subject_id", "phase"])[pc_cols].mean().reset_index()
        agg = agg.rename(columns={c: f"{mod}_{c}" for c in pc_cols})
        parts.append(agg)

    if not parts:
        return pd.DataFrame()

    result = parts[0]
    for part in parts[1:]:
        result = result.merge(part, on=["subject_id", "phase"], how="inner")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(subject_id: Optional[int] = None, verbose: bool = False) -> None:
    STAGE10_DATA_DIR.mkdir(parents=True, exist_ok=True)
    STAGE10_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    STAGE10_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    global_metrics: dict = {}
    modal_dfs: dict[str, pd.DataFrame] = {}

    le = LabelEncoder()

    for modality in MODALITIES:
        src = STAGE9_DATA_DIR / f"{modality}_selected.csv"
        if not src.exists():
            if verbose:
                print(f"[Stage 10] {modality.upper()} — input not found, skipping.")
            continue

        df = pd.read_csv(src)
        pc_cols = [c for c in df.columns if c.startswith("PC")]
        if not pc_cols or "phase" not in df.columns:
            continue

        X = df[pc_cols].values
        y = le.fit_transform(df["phase"])
        n_obs, n_feat = X.shape

        if verbose:
            print(f"\n[Stage 10] {modality.upper()} — {n_obs} obs × {n_feat} PCs")

        # VAL-001 VIF
        vif_df = _compute_vif(X, pc_cols)
        vif_mean = float(vif_df["vif"].mean())
        vif_max = float(vif_df["vif"].max())
        vif_ok = bool(vif_max < VIF_WARN)
        n_high_vif = int((vif_df["vif"] >= VIF_WARN).sum())
        if verbose:
            print(f"  VIF: mean={vif_mean:.3f}, max={vif_max:.3f}, "
                  f"n_high={n_high_vif} ({'OK' if vif_ok else 'WARN'})")

        # VAL-002 Separability
        sep = _separability_metrics(X, y, pc_cols)
        if verbose:
            print(f"  Separability: top_pc={sep['top_pc_by_f']}, "
                  f"F={sep['top_pc_f']:.2f}, η²={sep['top_pc_eta2']:.3f}, "
                  f"sep_ok={sep['separability_ok']}")

        # VAL-003 Balance
        bal = _balance_metrics(df["phase"])
        if verbose:
            print(f"  Balance: {bal['counts']}, ratio={bal['imbalance_ratio']:.2f} "
                  f"({'OK' if bal['balance_ok'] else 'WARN'})")

        # Figures
        _plot_density(df, pc_cols, modality)
        _plot_vif(vif_df, modality)
        _plot_balance(bal, modality)

        mod_metrics = {
            "modality": modality,
            "n_observations": n_obs,
            "n_features": n_feat,
            "class_balance": bal,
            "vif_mean": round(vif_mean, 4),
            "vif_max": round(vif_max, 4),
            "n_high_vif": n_high_vif,
            "vif_ok": vif_ok,
            "separability": sep,
            "dataset_ready": vif_ok and bal["balance_ok"],
        }

        with open(STAGE10_METRICS_DIR / f"{modality}_validation.json", "w") as f:
            json.dump(mod_metrics, f, indent=2)

        global_metrics[modality] = mod_metrics
        modal_dfs[modality] = df

    # VAL-005 Dataset final
    final_df = _assemble_final(modal_dfs)
    if not final_df.empty:
        final_df.to_csv(STAGE10_DATA_DIR / "dataset_final.csv", index=False)
        n_final_subjects = int(final_df["subject_id"].nunique())
        n_final_features = len([c for c in final_df.columns
                                 if c not in ("subject_id", "phase")])
        n_final_obs = len(final_df)
        if verbose:
            print(f"\n  Dataset final: {n_final_subjects} subjects, "
                  f"{n_final_obs} obs, {n_final_features} features")
    else:
        n_final_subjects = n_final_features = n_final_obs = 0

    global_metrics["dataset_final"] = {
        "n_subjects": n_final_subjects,
        "n_observations": n_final_obs,
        "n_features_total": n_final_features,
        "path": "output/stage10_validation/data/dataset_final.csv",
    }

    with open(STAGE10_METRICS_DIR / "final_validation.json", "w") as f:
        json.dump(global_metrics, f, indent=2)

    if verbose:
        print(f"\n[Stage 10] Complete. Output → {STAGE10_DATA_DIR}")
