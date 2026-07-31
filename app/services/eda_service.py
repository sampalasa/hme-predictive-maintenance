"""Exploratory Data Analysis (EDA) service.

Computes descriptive statistics and builds interactive Plotly figures over
the full HME_Downtime dataset (loaded fresh from the source Excel file, not
just what has been seeded into SQLite) so the EDA reflects the raw data
scientists would actually start from.
"""

import io
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.data.data_cleaning_service import DataCleaningService
from app.services.data.data_loader_service import DataLoaderService
from app.utils.logger import get_logger

logger = get_logger(__name__)

_NUMERIC_COLUMNS = ["OperatingHours", "EngineTemp", "HydraulicPressure", "Vibration"]


class EdaService:
    """Builds the exploratory data analysis report shown on the /eda page."""

    def __init__(self) -> None:
        self._df: pd.DataFrame | None = None

    def _get_dataframe(self) -> pd.DataFrame:
        if self._df is None:
            df = DataLoaderService().load()
            self._df = DataCleaningService().clean(df)
        return self._df

    def get_overview(self) -> dict[str, Any]:
        df = self._get_dataframe()

        return {
            "n_rows": int(len(df)),
            "n_columns": int(df.shape[1]),
            "columns": [
                {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "missing": int(df[col].isna().sum()),
                    "missing_pct": round(float(df[col].isna().mean() * 100), 2),
                }
                for col in df.columns
            ],
            "duplicate_rows": int(df.duplicated().sum()),
            "target_distribution": df["FailureWithin7Days"].value_counts().to_dict(),
            "target_rate_pct": round(float(df["FailureWithin7Days"].mean() * 100), 2),
        }

    def get_numeric_summary(self) -> list[dict[str, Any]]:
        df = self._get_dataframe()
        summary = df[_NUMERIC_COLUMNS].describe().T
        summary["skew"] = df[_NUMERIC_COLUMNS].skew()
        return [
            {"variable": idx, **{k: round(float(v), 3) for k, v in row.items()}}
            for idx, row in summary.iterrows()
        ]

    def build_histograms_figure(self) -> go.Figure:
        df = self._get_dataframe()
        fig = make_subplots(rows=2, cols=2, subplot_titles=_NUMERIC_COLUMNS)
        for i, col in enumerate(_NUMERIC_COLUMNS):
            row, coln = divmod(i, 2)
            fig.add_trace(go.Histogram(x=df[col], marker_color="#2563eb", name=col), row=row + 1, col=coln + 1)
        fig.update_layout(showlegend=False, height=550, title="Distribution des variables numériques")
        return fig

    def build_boxplots_figure(self) -> go.Figure:
        df = self._get_dataframe()
        fig = make_subplots(rows=1, cols=4, subplot_titles=_NUMERIC_COLUMNS)
        for i, col in enumerate(_NUMERIC_COLUMNS):
            fig.add_trace(go.Box(y=df[col], name=col, marker_color="#7c3aed"), row=1, col=i + 1)
        fig.update_layout(showlegend=False, height=420, title="Détection des valeurs aberrantes (Boxplots)")
        return fig

    def build_correlation_heatmap(self) -> go.Figure:
        df = self._get_dataframe()
        corr = df[_NUMERIC_COLUMNS + ["FailureWithin7Days"]].corr()
        fig = go.Figure(
            data=go.Heatmap(
                z=corr.values, x=corr.columns, y=corr.columns, colorscale="RdBu", zmid=0,
                text=corr.round(3).values, texttemplate="%{text}",
            )
        )
        fig.update_layout(title="Heatmap de corrélation", height=480)
        return fig

    def build_pairplot_figure(self, sample_size: int = 800) -> go.Figure:
        df = self._get_dataframe()
        sample = df.sample(min(sample_size, len(df)), random_state=42)
        fig = px.scatter_matrix(
            sample,
            dimensions=_NUMERIC_COLUMNS,
            color="FailureWithin7Days",
            color_continuous_scale=["#16a34a", "#dc2626"],
        )
        fig.update_layout(title=f"Pair Plot (échantillon n={len(sample)})", height=650)
        return fig

    def build_target_distribution_figure(self) -> go.Figure:
        df = self._get_dataframe()
        counts = df["FailureWithin7Days"].value_counts().rename({0: "Pas de panne", 1: "Panne sous 7 jours"})
        fig = go.Figure(data=go.Pie(labels=counts.index, values=counts.values, hole=0.45,
                                     marker_colors=["#16a34a", "#dc2626"]))
        fig.update_layout(title="Distribution de la variable cible")
        return fig

    def build_equipment_type_figure(self) -> go.Figure:
        df = self._get_dataframe()
        counts = df["EquipmentType"].value_counts()
        fig = go.Figure(data=go.Bar(x=counts.index, y=counts.values, marker_color="#0d9488"))
        fig.update_layout(title="Nombre de lectures par type d'équipement", height=380)
        return fig

    def build_failure_mode_figure(self) -> go.Figure:
        df = self._get_dataframe()
        rate = df.groupby("FailureMode")["FailureWithin7Days"].mean().sort_values(ascending=False) * 100
        fig = go.Figure(data=go.Bar(x=rate.index, y=rate.values, marker_color="#ea580c"))
        fig.update_layout(title="Taux de panne (%) par mode de panne observé", height=380)
        return fig

    def build_temporal_figure(self) -> go.Figure:
        df = self._get_dataframe()
        monthly = df.set_index("Timestamp").resample("ME")["FailureWithin7Days"].sum()
        fig = go.Figure(data=go.Scatter(x=monthly.index, y=monthly.values, mode="lines+markers", line_color="#2563eb"))
        fig.update_layout(title="Évolution temporelle des pannes détectées", height=380)
        return fig

    def export_pdf_report(self) -> bytes:
        """Render key EDA figures to static images (kaleido) and assemble a PDF."""

        overview = self.get_overview()
        numeric_summary = self.get_numeric_summary()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="Rapport EDA — HME_Downtime")
        styles = getSampleStyleSheet()
        story: list[Any] = []

        story.append(Paragraph("Rapport d'Analyse Exploratoire des Données (EDA)", styles["Title"]))
        story.append(Paragraph(f"Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
        story.append(Spacer(1, 14))

        story.append(Paragraph("1. Aperçu du dataset", styles["Heading2"]))
        story.append(
            Paragraph(
                f"{overview['n_rows']} lignes, {overview['n_columns']} colonnes, "
                f"{overview['duplicate_rows']} doublon(s), taux de panne cible = {overview['target_rate_pct']}%.",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 10))

        summary_rows = [["Variable", "Moyenne", "Écart-type", "Min", "Max", "Asymétrie"]] + [
            [s["variable"], s["mean"], s["std"], s["min"], s["max"], s["skew"]] for s in numeric_summary
        ]
        summary_table = Table(summary_rows, colWidths=[100, 70, 70, 60, 60, 70])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 16))

        story.append(Paragraph("2. Visualisations clés", styles["Heading2"]))
        figures = [
            ("Distribution de la variable cible", self.build_target_distribution_figure()),
            ("Heatmap de corrélation", self.build_correlation_heatmap()),
            ("Lectures par type d'équipement", self.build_equipment_type_figure()),
            ("Taux de panne par mode", self.build_failure_mode_figure()),
        ]
        for title, fig in figures:
            story.append(Paragraph(title, styles["Heading3"]))
            png_bytes = fig.to_image(format="png", width=700, height=400, scale=1.5)
            story.append(Image(io.BytesIO(png_bytes), width=430, height=246))
            story.append(Spacer(1, 12))

        doc.build(story)
        return buffer.getvalue()

    def get_all_figures_json(self) -> dict[str, str]:
        return {
            "histograms": self.build_histograms_figure().to_json(),
            "boxplots": self.build_boxplots_figure().to_json(),
            "correlation": self.build_correlation_heatmap().to_json(),
            "pairplot": self.build_pairplot_figure().to_json(),
            "target_distribution": self.build_target_distribution_figure().to_json(),
            "equipment_type": self.build_equipment_type_figure().to_json(),
            "failure_mode": self.build_failure_mode_figure().to_json(),
            "temporal": self.build_temporal_figure().to_json(),
        }
