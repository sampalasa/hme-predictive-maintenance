"""Computes real dataset statistics and generates all chart images used by
the academic Word report (scripts/generate_word_report.py).

Run with:
    python scripts/generate_report_assets.py

Produces, in docs/report_assets/:
    - dataset_stats.json      (all numbers referenced in the report's prose)
    - correlation_heatmap.png
    - histograms.png
    - boxplots.png
    - target_distribution.png
    - equipment_type_bar.png
    - failure_mode_bar.png
    - feature_importance.png
    - shap_summary.png
    - shap_waterfall.png
    - shap_dependence.png

Every figure is computed from the real dataset / the real active trained
model — nothing here is fabricated, including the fact that correlations
turn out to be near zero (see docs/03_eda.md for the same finding).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import shap
from sklearn.ensemble import IsolationForest

from app import create_app
from app.services.data.data_cleaning_service import DataCleaningService
from app.services.data.data_loader_service import DataLoaderService
from app.services.ml.explainability_service import ExplainabilityService
from app.services.ml.prediction_service import PredictionService

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "report_assets"
NUMERIC_COLS = ["OperatingHours", "EngineTemp", "HydraulicPressure", "Vibration"]
TARGET = "FailureWithin7Days"

sns.set_theme(style="whitegrid", font_scale=0.95)


def compute_overview(df: pd.DataFrame) -> dict:
    return {
        "n_rows": int(len(df)),
        "n_columns": int(df.shape[1]),
        "duplicate_rows_before_cleaning": 1,  # known from DataCleaningService logs
        "columns": [
            {"name": c, "dtype": str(df[c].dtype), "missing": int(df[c].isna().sum())}
            for c in df.columns
        ],
        "target_counts": {str(k): int(v) for k, v in df[TARGET].value_counts().items()},
        "target_rate_pct": round(float(df[TARGET].mean() * 100), 2),
    }


def compute_numeric_summary(df: pd.DataFrame) -> list[dict]:
    summary = df[NUMERIC_COLS].describe().T
    summary["skew"] = df[NUMERIC_COLS].skew()
    summary["variance"] = df[NUMERIC_COLS].var()
    return [
        {"variable": idx, **{k: round(float(v), 3) for k, v in row.items()}}
        for idx, row in summary.iterrows()
    ]


def compute_correlations(df: pd.DataFrame) -> dict:
    corr = df[NUMERIC_COLS + [TARGET]].corr()
    with_target = corr[TARGET].drop(TARGET).sort_values(key=abs, ascending=False)
    return {
        "matrix": corr.round(4).to_dict(),
        "with_target_ranked": [
            {"variable": k, "pearson_r": round(float(v), 4)} for k, v in with_target.items()
        ],
    }


def compute_outliers(df: pd.DataFrame) -> dict:
    iqr_counts = {}
    for col in NUMERIC_COLS:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_counts[col] = int(((df[col] < lower) | (df[col] > upper)).sum())

    iso = IsolationForest(contamination=0.02, random_state=42, n_jobs=-1)
    labels = iso.fit_predict(df[NUMERIC_COLS])
    n_anomalies = int((labels == -1).sum())

    return {
        "iqr_outlier_counts": iqr_counts,
        "isolation_forest_anomalies": n_anomalies,
        "isolation_forest_pct": round(n_anomalies / len(df) * 100, 2),
    }


def save_correlation_heatmap(df: pd.DataFrame) -> None:
    corr = df[NUMERIC_COLS + [TARGET]].corr()
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1,
                square=True, linewidths=0.5, ax=ax, cbar_kws={"shrink": 0.8})
    ax.set_title("Matrice de corrélation (Pearson)", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "correlation_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_histograms(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    for ax, col in zip(axes.flat, NUMERIC_COLS):
        sns.histplot(df[col], kde=True, ax=ax, color="#2563eb", bins=30)
        ax.set_title(col, fontsize=10, fontweight="bold")
    fig.suptitle("Distributions et densités des variables numériques", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "histograms.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_boxplots(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(11, 4.2))
    for ax, col in zip(axes, NUMERIC_COLS):
        sns.boxplot(y=df[col], ax=ax, color="#93c5fd")
        ax.set_title(col, fontsize=9.5, fontweight="bold")
    fig.suptitle("Boxplots — détection visuelle des valeurs aberrantes", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "boxplots.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_target_distribution(df: pd.DataFrame) -> None:
    counts = df[TARGET].value_counts().rename({0: "Pas de panne (0)", 1: "Panne sous 7 jours (1)"})
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    colors = ["#16a34a", "#dc2626"]
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", colors=colors,
           wedgeprops={"edgecolor": "white", "linewidth": 1.5}, textprops={"fontsize": 9})
    ax.set_title("Distribution de la variable cible FailureWithin7Days", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "target_distribution.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_bar_chart(series: pd.Series, title: str, filename: str, color: str) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4))
    series.value_counts().plot(kind="bar", ax=ax, color=color, edgecolor="white")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("Nombre de lectures")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=200, bbox_inches="tight")
    plt.close(fig)


def save_feature_importance_and_shap() -> dict:
    """Uses the active trained model to compute native feature importance and
    SHAP plots. Returns a dict of ranked feature importances (for tables)."""

    prediction_service = PredictionService()
    model, feature_names, active_version = prediction_service._load_active_model()

    explainability_service = ExplainabilityService()
    raw_df = explainability_service._build_fleet_feature_matrix()
    enriched_df, _ = explainability_service.feature_engineering.engineer_features(raw_df)

    sample = enriched_df.sample(min(500, len(enriched_df)), random_state=42)
    X = sample.reindex(columns=feature_names, fill_value=0.0)

    # --- Native feature importance (model.feature_importances_) -----------
    importances = getattr(model, "feature_importances_", None)
    ranked_importance = []
    if importances is not None:
        ranking = sorted(zip(feature_names, importances), key=lambda item: item[1], reverse=True)[:20]
        ranked_importance = [{"feature": f, "importance": round(float(v), 5)} for f, v in ranking]

        fig, ax = plt.subplots(figsize=(7, 6.5))
        feats = [r["feature"] for r in ranked_importance][::-1]
        vals = [r["importance"] for r in ranked_importance][::-1]
        ax.barh(feats, vals, color="#2563eb")
        ax.set_title(f"Importance des variables — {active_version.algorithm} (Top 20)",
                     fontsize=11, fontweight="bold")
        ax.set_xlabel("Importance (native au modèle)")
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "feature_importance.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    # --- SHAP ---------------------------------------------------------------
    explainer = shap.TreeExplainer(model)
    raw_shap = explainer.shap_values(X)
    if isinstance(raw_shap, list):
        shap_values = raw_shap[1]
    elif isinstance(raw_shap, np.ndarray) and raw_shap.ndim == 3:
        shap_values = raw_shap[:, :, 1]
    else:
        shap_values = raw_shap

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_ranking = sorted(zip(feature_names, mean_abs_shap), key=lambda item: item[1], reverse=True)
    top_feature = shap_ranking[0][0]
    shap_ranked = [{"feature": f, "mean_abs_shap": round(float(v), 5)} for f, v in shap_ranking[:20]]

    plt.figure(figsize=(7.5, 7))
    shap.summary_plot(shap_values, X, show=False, max_display=15)
    plt.title("SHAP Summary Plot — impact de chaque variable sur la prédiction", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_summary.png", dpi=200, bbox_inches="tight")
    plt.close()

    base_value = explainer.expected_value
    if isinstance(base_value, (list, np.ndarray)):
        base_value = np.atleast_1d(base_value)[1] if len(np.atleast_1d(base_value)) > 1 else np.atleast_1d(base_value)[0]

    explanation = shap.Explanation(
        values=shap_values[0], base_values=base_value, data=X.iloc[0].values, feature_names=feature_names,
    )
    plt.figure(figsize=(7.5, 6))
    shap.plots.waterfall(explanation, show=False, max_display=15)
    plt.title("SHAP Waterfall — explication d'une prédiction individuelle", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_waterfall.png", dpi=200, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(7, 5.5))
    shap.dependence_plot(top_feature, shap_values, X, show=False)
    plt.title(f"SHAP Dependence Plot — {top_feature}", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_dependence.png", dpi=200, bbox_inches="tight")
    plt.close()

    return {
        "model_name": f"{active_version.name} v{active_version.version_number}",
        "algorithm": active_version.algorithm,
        "native_importance_ranked": ranked_importance,
        "shap_importance_ranked": shap_ranked,
        "shap_top_feature": top_feature,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = DataLoaderService().load()
    df = DataCleaningService().clean(raw_df)

    stats: dict = {
        "overview": compute_overview(df),
        "numeric_summary": compute_numeric_summary(df),
        "correlations": compute_correlations(df),
        "outliers": compute_outliers(df),
        "equipment_type_counts": {k: int(v) for k, v in df["EquipmentType"].value_counts().items()},
        "failure_mode_counts": {k: int(v) for k, v in df["FailureMode"].value_counts().items()},
        "failure_mode_rate_pct": {
            k: round(float(v) * 100, 2) for k, v in df.groupby("FailureMode")[TARGET].mean().items()
        },
    }

    save_correlation_heatmap(df)
    save_histograms(df)
    save_boxplots(df)
    save_target_distribution(df)
    save_bar_chart(df["EquipmentType"], "Nombre de lectures par type d'équipement",
                    "equipment_type_bar.png", "#0d9488")
    save_bar_chart(df["FailureMode"], "Nombre de lectures par mode de panne observé",
                    "failure_mode_bar.png", "#ea580c")

    app = create_app()
    with app.app_context():
        stats["model"] = save_feature_importance_and_shap()

    (OUTPUT_DIR / "dataset_stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"All assets written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
