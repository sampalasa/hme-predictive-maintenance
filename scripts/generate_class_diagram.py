"""Generates the UML Class Diagram of the domain model (SQLAlchemy models) as PNG.

Run with:
    python scripts/generate_class_diagram.py

Produces docs/diagrams/class_diagram.png — the 12 SQLAlchemy models under
app/models/, their attributes (as actually declared in the code), and their
relationships: inheritance (User --|> UserMixin), composition (Equipment *--
EquipmentReading / MaintenanceRecord, cascade delete-orphan in the code),
aggregation (User o-- Report / Notification / AuditLog) and plain
associations (Equipment/ModelVersion -- Prediction, ModelVersion --
TrainingRun).

Rendered with matplotlib only (no Graphviz/PlantUML/Java dependency) — same
reasoning as the other diagrams, see docs/08_mlops.md.
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

TITLE_BG = "#2563eb"
BODY_BG = "#eff6ff"
EDGE_COLOR = "#1e293b"
MIXIN_BG = "#f1f5f9"

ATTR_LINE_H = 0.40
TITLE_H = 0.85
STEREOTYPE_H = 0.38


def draw_class_box(ax, x, y_top, title, attrs, width=4.8, stereotype=None):
    """Draws a UML class box with its top-left-ish anchor at (x, y_top).

    Returns a dict of anchor points (top/bottom/left/right/center) on the
    box boundary, used to attach relationship lines.
    """

    extra = STEREOTYPE_H if stereotype else 0
    height = TITLE_H + extra + len(attrs) * ATTR_LINE_H + 0.25

    box = mpatches.FancyBboxPatch(
        (x, y_top - height), width, height,
        boxstyle="square,pad=0.0", facecolor=BODY_BG, edgecolor=EDGE_COLOR, linewidth=1.2, zorder=2,
    )
    ax.add_patch(box)

    title_box = mpatches.Rectangle(
        (x, y_top - TITLE_H), width, TITLE_H, facecolor=TITLE_BG, edgecolor=EDGE_COLOR, linewidth=1.2, zorder=3,
    )
    ax.add_patch(title_box)
    ax.text(x + width / 2, y_top - TITLE_H / 2, title, ha="center", va="center",
            fontsize=9.5, fontweight="bold", color="white", zorder=4)

    y_cursor = y_top - TITLE_H
    if stereotype:
        ax.text(x + width / 2, y_cursor - STEREOTYPE_H / 2, stereotype, ha="center", va="center",
                fontsize=7.5, fontstyle="italic", color="#475569", zorder=4)
        y_cursor -= STEREOTYPE_H
        ax.plot([x, x + width], [y_cursor, y_cursor], color=EDGE_COLOR, linewidth=0.8, zorder=3)

    for attr in attrs:
        y_cursor -= ATTR_LINE_H
        ax.text(x + 0.15, y_cursor + ATTR_LINE_H * 0.15, attr, ha="left", va="center",
                fontsize=7.3, color="#0f172a", zorder=4, family="monospace")

    y_bottom = y_top - height
    return {
        "top": (x + width / 2, y_top),
        "bottom": (x + width / 2, y_bottom),
        "left": (x, y_top - height / 2),
        "right": (x + width, y_top - height / 2),
        "height": height,
        "x": x, "y_top": y_top, "width": width,
    }


def add_diamond(ax, point, direction, filled, size=0.24):
    dx, dy = direction
    length = (dx ** 2 + dy ** 2) ** 0.5
    dx, dy = dx / length, dy / length
    px, py = -dy, dx
    back = (point[0] - dx * size * 2.1, point[1] - dy * size * 2.1)
    left = (back[0] + px * size, back[1] + py * size)
    right = (back[0] - px * size, back[1] - py * size)
    far = (point[0] - dx * size * 4.2, point[1] - dy * size * 4.2)
    poly = mpatches.Polygon(
        [point, left, far, right], closed=True,
        facecolor="black" if filled else "white", edgecolor=EDGE_COLOR, linewidth=1.1, zorder=5,
    )
    ax.add_patch(poly)
    return far  # the line should stop here, diamond fills the rest


def add_triangle(ax, point, direction, size=0.42):
    dx, dy = direction
    length = (dx ** 2 + dy ** 2) ** 0.5
    dx, dy = dx / length, dy / length
    px, py = -dy, dx
    back = (point[0] - dx * size * 1.8, point[1] - dy * size * 1.8)
    left = (back[0] + px * size * 0.8, back[1] + py * size * 0.8)
    right = (back[0] - px * size * 0.8, back[1] - py * size * 0.8)
    poly = mpatches.Polygon(
        [point, left, right], closed=True, facecolor="white", edgecolor=EDGE_COLOR, linewidth=1.2, zorder=5,
    )
    ax.add_patch(poly)
    return back


def relationship(ax, p_owner, p_other, kind, mult_owner="", mult_other="", curve=0.0):
    """kind in {composition, aggregation, association, inheritance}.

    For composition/aggregation/inheritance, the marker sits at p_owner
    (the whole / the parent). p_owner and p_other are (x, y) tuples.
    """

    direction = (p_other[0] - p_owner[0], p_other[1] - p_owner[1])
    line_start = p_owner

    if kind == "composition":
        line_start = add_diamond(ax, p_owner, direction, filled=True)
    elif kind == "aggregation":
        line_start = add_diamond(ax, p_owner, direction, filled=False)
    elif kind == "inheritance":
        line_start = add_triangle(ax, p_owner, direction)

    if curve == 0.0:
        ax.plot([line_start[0], p_other[0]], [line_start[1], p_other[1]], color=EDGE_COLOR, linewidth=1.1, zorder=1)
    else:
        ax.annotate(
            "", xy=p_other, xytext=line_start,
            arrowprops=dict(arrowstyle="-", color=EDGE_COLOR, lw=1.1, connectionstyle=f"arc3,rad={curve}"),
            zorder=1,
        )

    if mult_owner:
        ax.text(p_owner[0] + (0.35 if direction[0] >= 0 else -0.55), p_owner[1] + 0.25,
                mult_owner, fontsize=7.2, color="#b45309", zorder=6)
    if mult_other:
        ax.text(p_other[0] + (-0.55 if direction[0] >= 0 else 0.35), p_other[1] + 0.25,
                mult_other, fontsize=7.2, color="#b45309", zorder=6)


def build_diagram() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(24, 18))
    ax.set_xlim(-4, 30)
    ax.set_ylim(0, 42)
    ax.axis("off")
    ax.set_title(
        "Diagramme de Classes — Modèle de Domaine (SQLAlchemy)",
        fontsize=16, fontweight="bold", color="#0f172a", pad=18,
    )

    # ---- Column A (x=0): Role, User, Report, Notification, AuditLog --------
    role = draw_class_box(ax, 0, 41, "Role", [
        "+ id: int [PK]", "+ name: str", "+ description: str", "+ created_at: datetime",
    ])
    user = draw_class_box(ax, 0, role["bottom"][1] - 1.4, "User", [
        "+ id: int [PK]", "+ username: str", "+ email: str", "+ password_hash: str",
        "+ full_name: str", "+ role_id: int [FK]", "+ is_active: bool",
        "+ last_login_at: datetime", "+ created_at: datetime",
    ])
    user_mixin = draw_class_box(ax, -3.6, user["y_top"] - (user["height"] / 2) + 0.7, "UserMixin", [],
                                 width=2.9, stereotype="«mixin» (Flask-Login)")

    report = draw_class_box(ax, 0, user["bottom"][1] - 1.4, "Report", [
        "+ id: int [PK]", "+ title: str", "+ report_type: str", "+ file_path: str",
        "+ generated_by_id: int [FK, null]", "+ generated_at: datetime",
    ])
    notification = draw_class_box(ax, 0, report["bottom"][1] - 1.4, "Notification", [
        "+ id: int [PK]", "+ user_id: int [FK, null]", "+ title: str", "+ message: str",
        "+ level: str", "+ is_read: bool", "+ created_at: datetime",
    ])
    audit_log = draw_class_box(ax, 0, notification["bottom"][1] - 1.4, "AuditLog", [
        "+ id: int [PK]", "+ user_id: int [FK, null]", "+ action: str", "+ entity_type: str",
        "+ entity_id: int", "+ details: str", "+ created_at: datetime",
    ])

    # ---- Column B (x=9.5): Equipment, Prediction, Setting ------------------
    equipment = draw_class_box(ax, 9.5, 39, "Equipment", [
        "+ id: int [PK]", "+ equipment_code: str", "+ equipment_type: str",
        "+ status: str", "+ site: str", "+ created_at: datetime",
    ])
    prediction = draw_class_box(ax, 9.5, equipment["bottom"][1] - 4.4, "Prediction", [
        "+ id: int [PK]", "+ equipment_id: int [FK]", "+ model_version_id: int [FK]",
        "+ probability: float", "+ predicted_label: int", "+ risk_level: str",
        "+ input_features_json: str", "+ created_at: datetime",
    ])
    setting = draw_class_box(ax, 9.5, prediction["bottom"][1] - 5.0, "Setting", [
        "+ id: int [PK]", "+ key: str", "+ value: str", "+ description: str", "+ updated_at: datetime",
    ])
    ax.text(9.5 + 2.4, setting["y_top"] + 0.4, "(aucune relation — clé/valeur globale)",
            fontsize=7.5, fontstyle="italic", color="#64748b")

    # ---- Column C (x=19): EquipmentReading, MaintenanceRecord, ModelVersion, TrainingRun
    reading = draw_class_box(ax, 19, 39, "EquipmentReading", [
        "+ id: int [PK]", "+ equipment_id: int [FK]", "+ timestamp: datetime",
        "+ operating_hours: int", "+ engine_temp: float", "+ hydraulic_pressure: float",
        "+ vibration: float", "+ failure_mode: str", "+ failure_within_7_days: int",
    ])
    maintenance = draw_class_box(ax, 19, reading["bottom"][1] - 1.4, "MaintenanceRecord", [
        "+ id: int [PK]", "+ equipment_id: int [FK]", "+ maintenance_type: str",
        "+ description: str", "+ performed_by: str", "+ downtime_hours: float",
        "+ cost: float", "+ status: str", "+ performed_at: datetime",
    ])
    model_version = draw_class_box(ax, 19, maintenance["bottom"][1] - 1.4, "ModelVersion", [
        "+ id: int [PK]", "+ name: str", "+ algorithm: str", "+ version_number: str",
        "+ file_path: str", "+ feature_list_path: str", "+ metrics_json: str",
        "+ hyperparameters_json: str", "+ is_active: bool", "+ trained_at: datetime",
    ])
    training_run = draw_class_box(ax, 19, model_version["bottom"][1] - 1.4, "TrainingRun", [
        "+ id: int [PK]", "+ model_version_id: int [FK, null]", "+ status: str",
        "+ leaderboard_json: str", "+ notes: str", "+ started_at: datetime", "+ completed_at: datetime",
    ])

    # ---- Relationships -------------------------------------------------------
    # Inheritance: hollow triangle sits at the PARENT (UserMixin) end.
    relationship(ax, user_mixin["right"], user["left"], "inheritance")
    relationship(ax, role["bottom"], user["top"], "association", "1", "*")

    # Distinct anchor points along User's right edge so the three aggregation
    # diamonds don't stack on top of each other.
    user_right_25 = (user["x"] + user["width"], user["y_top"] - user["height"] * 0.25)
    user_right_50 = (user["x"] + user["width"], user["y_top"] - user["height"] * 0.5)
    user_right_75 = (user["x"] + user["width"], user["y_top"] - user["height"] * 0.75)
    relationship(ax, user_right_25, report["right"], "aggregation", "1", "*", curve=0.5)
    relationship(ax, user_right_50, notification["right"], "aggregation", "1", "*", curve=0.65)
    relationship(ax, user_right_75, audit_log["right"], "aggregation", "1", "*", curve=0.85)

    # Distinct anchor points along Equipment's right edge for its two
    # composition relationships (same fix as above).
    equipment_right_30 = (equipment["x"] + equipment["width"], equipment["y_top"] - equipment["height"] * 0.3)
    equipment_right_75 = (equipment["x"] + equipment["width"], equipment["y_top"] - equipment["height"] * 0.75)
    relationship(ax, equipment_right_30, reading["left"], "composition", "1", "*")
    relationship(ax, equipment_right_75, maintenance["left"], "composition", "1", "*", curve=-0.25)
    relationship(ax, equipment["bottom"], prediction["top"], "association", "1", "*")

    relationship(ax, model_version["left"], prediction["right"], "association", "1", "*")
    relationship(ax, model_version["bottom"], training_run["top"], "association", "1", "0..*")

    # ---- Legend ---------------------------------------------------------------
    legend_items = [
        mpatches.Patch(facecolor="white", edgecolor=EDGE_COLOR, label="— Association"),
        mpatches.Patch(facecolor="black", edgecolor=EDGE_COLOR, label="◆ Composition (cascade delete-orphan)"),
        mpatches.Patch(facecolor="white", edgecolor=EDGE_COLOR, label="◇ Agrégation"),
        mpatches.Patch(facecolor="white", edgecolor=EDGE_COLOR, label="▷ Héritage (generalization)"),
    ]
    ax.legend(handles=legend_items, loc="lower right", frameon=True, fontsize=8.5)

    fig.tight_layout()
    return fig


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = build_diagram()
    output_path = OUTPUT_DIR / "class_diagram.png"
    fig.savefig(output_path, dpi=170, bbox_inches="tight", facecolor="white")
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
