"""Generates downloadable reports: CSV, Excel and PDF.

Each export also logs a ``Report`` row so generated documents are traceable
from the admin panel, per the "Rapports IA / Rapports statistiques"
requirement.
"""

import io
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Report, db
from app.services.dashboard_service import DashboardService
from app.services.equipment_service import EquipmentService


class ReportService:
    """Builds report files in-memory (CSV/Excel/PDF) ready to stream to the client."""

    def __init__(self) -> None:
        self.equipment_service = EquipmentService()
        self.dashboard_service = DashboardService()

    def equipment_overview_csv(self) -> bytes:
        df = pd.DataFrame(self.equipment_service.list_equipment_overview())
        return df.to_csv(index=False).encode("utf-8")

    def predictions_excel(self) -> bytes:
        df = pd.DataFrame(self.equipment_service.get_latest_predictions_ranked())
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Predictions")
        return buffer.getvalue()

    def maintenance_csv(self) -> bytes:
        df = pd.DataFrame(self.dashboard_service.get_recent_maintenance(limit=10_000))
        return df.to_csv(index=False).encode("utf-8")

    def fleet_summary_pdf(self) -> bytes:
        kpis = self.dashboard_service.get_summary_kpis()
        top_critical = self.dashboard_service.get_top_critical_equipment(limit=15)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="Rapport de synthèse — Flotte HME")
        styles = getSampleStyleSheet()
        story: list[Any] = []

        story.append(Paragraph("Rapport de synthèse — Maintenance prédictive HME", styles["Title"]))
        story.append(
            Paragraph(
                f"Généré le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 16))

        story.append(Paragraph("Indicateurs clés de performance", styles["Heading2"]))
        kpi_rows = [["Indicateur", "Valeur"]] + [
            [label, str(kpis[key])]
            for key, label in [
                ("total_equipment", "Équipements"),
                ("total_failures", "Pannes détectées"),
                ("availability_pct", "Disponibilité (%)"),
                ("mtbf_hours", "MTBF (h)"),
                ("mttr_hours", "MTTR (h)"),
                ("predictions_today", "Prédictions aujourd'hui"),
                ("critical_equipment", "Équipements critiques"),
            ]
        ]
        kpi_table = Table(kpi_rows, colWidths=[220, 120])
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(kpi_table)
        story.append(Spacer(1, 20))

        story.append(Paragraph("Top équipements les plus sujets aux pannes", styles["Heading2"]))
        crit_rows = [["Équipement", "Type", "Nb. pannes"]] + [
            [row["equipment_code"], row["equipment_type"], str(row["failures"])] for row in top_critical
        ]
        crit_table = Table(crit_rows, colWidths=[140, 140, 100])
        crit_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ef4444")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(crit_table)

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def log_report(title: str, report_type: str, file_path: str, generated_by_id: int | None) -> None:
        db.session.add(
            Report(
                title=title,
                report_type=report_type,
                file_path=file_path,
                generated_by_id=generated_by_id,
            )
        )
        db.session.commit()
