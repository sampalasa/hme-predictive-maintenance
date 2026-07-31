"""Generates the full-project UML Use Case Diagram as a PNG image.

Run with:
    python scripts/generate_use_case_diagram.py

Produces:
    docs/diagrams/use_case_diagram.png   (rendered image)
    docs/diagrams/use_case_diagram.puml  (PlantUML source, for reference /
                                           re-rendering with a real PlantUML
                                           engine if one becomes available)

Rendered with matplotlib only (no Graphviz/PlantUML/Java dependency), since
neither a `dot` binary nor a Java runtime is available in this environment —
see docs/08_mlops.md for the same "actually runnable over decorative" choice
applied elsewhere in this project.
"""

import textwrap
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

ACTOR_COLOR = "#1e293b"
BOUNDARY_COLOR = "#2563eb"
COMMON_UC_COLOR = "#dbeafe"
ROLE_UC_COLOR = "#fef3c7"
CLI_UC_COLOR = "#dcfce7"
API_UC_COLOR = "#fee2e2"


def draw_actor(ax, x: float, y: float, label: str) -> tuple[float, float]:
    """Draws a simple UML stick-figure actor centered at (x, y). Returns the
    connection point (bottom of the figure) used for association lines."""

    head = mpatches.Circle((x, y + 0.55), 0.22, fill=False, edgecolor=ACTOR_COLOR, linewidth=1.6)
    ax.add_patch(head)
    ax.plot([x, x], [y + 0.33, y - 0.35], color=ACTOR_COLOR, linewidth=1.6)  # body
    ax.plot([x - 0.35, x + 0.35], [y + 0.05, y + 0.05], color=ACTOR_COLOR, linewidth=1.6)  # arms
    ax.plot([x, x - 0.3], [y - 0.35, y - 0.75], color=ACTOR_COLOR, linewidth=1.6)  # leg 1
    ax.plot([x, x + 0.3], [y - 0.35, y - 0.75], color=ACTOR_COLOR, linewidth=1.6)  # leg 2
    ax.text(x, y - 1.05, label, ha="center", va="top", fontsize=9.5, fontweight="bold", color=ACTOR_COLOR)
    return x, y - 0.75


def draw_use_case(ax, x: float, y: float, label: str, color: str, width: float = 2.9, height: float = 0.95):
    wrapped = "\n".join(textwrap.wrap(label, width=22))
    ellipse = mpatches.Ellipse(
        (x, y), width, height, facecolor=color, edgecolor="#334155", linewidth=1.1, zorder=2
    )
    ax.add_patch(ellipse)
    ax.text(x, y, wrapped, ha="center", va="center", fontsize=7.6, color="#0f172a", zorder=3)
    return x, y


def connect(ax, p1, p2, style: str = "-", color: str = "#64748b", lw: float = 0.9):
    ax.add_line(Line2D([p1[0], p2[0]], [p1[1], p2[1]], linestyle=style, color=color, linewidth=lw, zorder=1))


def connect_generalization(ax, child, parent):
    """UML generalization: solid line with a hollow triangle arrowhead at the parent end."""

    ax.annotate(
        "",
        xy=parent,
        xytext=child,
        arrowprops=dict(arrowstyle="-|>,head_width=0.5,head_length=0.9", color=ACTOR_COLOR, lw=1.2, fill=False),
        zorder=1,
    )


def build_diagram() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(24, 17))
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 19)
    ax.axis("off")
    ax.set_title(
        "Diagramme de Cas d'Utilisation — Système Intelligent de Maintenance Prédictive HME",
        fontsize=16, fontweight="bold", color="#0f172a", pad=18,
    )

    # ---- System boundary -------------------------------------------------
    boundary = mpatches.FancyBboxPatch(
        (3.6, 0.6), 15.8, 17.6, boxstyle="round,pad=0.02", linewidth=1.8,
        edgecolor=BOUNDARY_COLOR, facecolor="none", zorder=0,
    )
    ax.add_patch(boundary)
    ax.text(11.5, 18.55, "Système de Maintenance Prédictive HME (Web + API)",
            ha="center", fontsize=11, fontweight="bold", color=BOUNDARY_COLOR)

    # ---- Human actors (left) ---------------------------------------------
    admin = draw_actor(ax, 1.1, 16.8, "Admin")
    ingenieur = draw_actor(ax, 1.1, 13.3, "Ingénieur")
    technicien = draw_actor(ax, 1.1, 9.8, "Technicien")
    manager = draw_actor(ax, 1.1, 6.3, "Manager")
    abstract_actor = draw_actor(ax, 2.6, 2.4, "«abstract»\nUtilisateur\nauthentifié")

    for child in (admin, ingenieur, technicien, manager):
        connect_generalization(ax, child, abstract_actor)

    # ---- Common use cases (all authenticated roles) -----------------------
    common_labels = [
        "Se connecter (session web)",
        "Se déconnecter",
        "Consulter le tableau de bord (KPIs)",
        "Consulter la liste des équipements",
        "Consulter la fiche équipement",
        "Lancer une prédiction individuelle",
        "Lancer une prédiction par lot (CSV)",
        "Consulter les équipements à risque",
        "Consulter l'explicabilité (SHAP)",
        "Consulter l'analyse exploratoire (EDA)",
        "Consulter la sélection de variables",
        "Consulter l'évaluation du modèle",
        "Exporter un rapport / la documentation",
        "Recevoir une notification critique",
    ]
    common_points = []
    col_x = [6.0, 9.3]
    start_y, step_y = 17.6, 2.45
    for i, label in enumerate(common_labels):
        x = col_x[i % 2]
        y = start_y - (i // 2) * step_y
        common_points.append(draw_use_case(ax, x, y, label, COMMON_UC_COLOR))

    # single association from the abstract actor to each common use case
    for p in common_points:
        connect(ax, abstract_actor, p, color="#94a3b8")

    # ---- Role-specific use cases -------------------------------------------
    role_labels = [
        ("Enregistrer une maintenance", ["Ingénieur", "Technicien", "Admin"]),
        ("Créer un équipement", ["Ingénieur", "Admin"]),
        ("Modifier un équipement", ["Ingénieur", "Admin"]),
        ("Lancer la prédiction sur toute la flotte", ["Ingénieur", "Admin"]),
        ("Supprimer un équipement", ["Admin"]),
        ("Gérer les utilisateurs", ["Admin"]),
        ("Consulter le journal d'audit", ["Admin"]),
        ("Gérer les paramètres système", ["Admin"]),
        ("Consulter l'historique d'entraînement", ["Admin"]),
        ("Consulter la dérive des données (Data Drift)", ["Admin"]),
    ]
    actor_points = {"Admin": admin, "Ingénieur": ingenieur, "Technicien": technicien}
    role_x = 12.7
    start_y2 = 17.9
    for i, (label, roles) in enumerate(role_labels):
        y = start_y2 - i * 1.75
        p = draw_use_case(ax, role_x, y, label, ROLE_UC_COLOR, width=3.3)
        for role in roles:
            connect(ax, actor_points[role], p, color="#b45309", lw=0.8)

    # ---- Data Scientist actor (CLI / offline training) ---------------------
    data_scientist = draw_actor(ax, 20.6, 15.5, "Data\nScientist\n(CLI)")
    cli_labels = [
        "Entraîner le modèle (AutoML + Optuna)",
        "Réentraîner automatiquement\n(déclenché par Data Drift)",
    ]
    cli_x = 17.3
    for i, label in enumerate(cli_labels):
        y = 15.8 - i * 2.0
        p = draw_use_case(ax, cli_x, y, label.replace("\n", " "), CLI_UC_COLOR, width=3.1)
        connect(ax, data_scientist, p, color="#15803d")

    # ---- External system actor (public REST API) ---------------------------
    external_system = draw_actor(ax, 20.6, 8.5, "Système externe /\nIntégration (API)")
    api_labels = [
        "S'authentifier via API (JWT)",
        "Prédire via API REST\n(individuelle / flotte)",
        "Gérer les équipements via API (CRUD)",
    ]
    for i, label in enumerate(api_labels):
        y = 10.6 - i * 2.0
        p = draw_use_case(ax, cli_x, y, label.replace("\n", " "), API_UC_COLOR, width=3.1)
        connect(ax, external_system, p, color="#b91c1c")

    # ---- Legend -------------------------------------------------------------
    legend_items = [
        mpatches.Patch(facecolor=COMMON_UC_COLOR, edgecolor="#334155", label="Cas d'utilisation communs"),
        mpatches.Patch(facecolor=ROLE_UC_COLOR, edgecolor="#334155", label="Cas d'utilisation par rôle"),
        mpatches.Patch(facecolor=CLI_UC_COLOR, edgecolor="#334155", label="Cas d'utilisation CLI (Data Scientist)"),
        mpatches.Patch(facecolor=API_UC_COLOR, edgecolor="#334155", label="Cas d'utilisation API REST"),
    ]
    ax.legend(handles=legend_items, loc="lower center", ncol=4, frameon=False,
              bbox_to_anchor=(0.5, -0.02), fontsize=9)

    fig.tight_layout()
    return fig


def build_plantuml_source() -> str:
    return """@startuml
left to right direction
skinparam packageStyle rect
skinparam actorStyle awesome

actor Admin
actor "Ingénieur" as Ingenieur
actor Technicien
actor Manager
actor "Utilisateur authentifié" as AuthUser << abstract >>
actor "Data Scientist (CLI)" as DataScientist
actor "Système externe / Intégration" as ExternalSystem

Admin --|> AuthUser
Ingenieur --|> AuthUser
Technicien --|> AuthUser
Manager --|> AuthUser

rectangle "Système de Maintenance Prédictive HME (Web + API)" {
  usecase "Se connecter" as UC1
  usecase "Se déconnecter" as UC2
  usecase "Consulter le tableau de bord (KPIs)" as UC3
  usecase "Consulter la liste des équipements" as UC4
  usecase "Consulter la fiche équipement" as UC5
  usecase "Lancer une prédiction individuelle" as UC6
  usecase "Lancer une prédiction par lot (CSV)" as UC7
  usecase "Consulter les équipements à risque" as UC8
  usecase "Consulter l'explicabilité (SHAP)" as UC9
  usecase "Consulter l'analyse exploratoire (EDA)" as UC10
  usecase "Consulter la sélection de variables" as UC11
  usecase "Consulter l'évaluation du modèle" as UC12
  usecase "Exporter un rapport / la documentation" as UC13
  usecase "Recevoir une notification critique" as UC14

  usecase "Enregistrer une maintenance" as UC15
  usecase "Créer un équipement" as UC16
  usecase "Modifier un équipement" as UC17
  usecase "Lancer la prédiction sur toute la flotte" as UC18
  usecase "Supprimer un équipement" as UC19
  usecase "Gérer les utilisateurs" as UC20
  usecase "Consulter le journal d'audit" as UC21
  usecase "Gérer les paramètres système" as UC22
  usecase "Consulter l'historique d'entraînement" as UC23
  usecase "Consulter la dérive des données (Data Drift)" as UC24

  usecase "Entraîner le modèle (AutoML + Optuna)" as UC25
  usecase "Réentraîner automatiquement (drift)" as UC26

  usecase "S'authentifier via API (JWT)" as UC27
  usecase "Prédire via API REST" as UC28
  usecase "Gérer les équipements via API (CRUD)" as UC29
}

AuthUser --> UC1
AuthUser --> UC2
AuthUser --> UC3
AuthUser --> UC4
AuthUser --> UC5
AuthUser --> UC6
AuthUser --> UC7
AuthUser --> UC8
AuthUser --> UC9
AuthUser --> UC10
AuthUser --> UC11
AuthUser --> UC12
AuthUser --> UC13
AuthUser --> UC14

Ingenieur --> UC15
Technicien --> UC15
Admin --> UC15

Ingenieur --> UC16
Admin --> UC16
Ingenieur --> UC17
Admin --> UC17
Ingenieur --> UC18
Admin --> UC18

Admin --> UC19
Admin --> UC20
Admin --> UC21
Admin --> UC22
Admin --> UC23
Admin --> UC24

DataScientist --> UC25
DataScientist --> UC26

ExternalSystem --> UC27
ExternalSystem --> UC28
ExternalSystem --> UC29
@enduml
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig = build_diagram()
    png_path = OUTPUT_DIR / "use_case_diagram.png"
    fig.savefig(png_path, dpi=170, bbox_inches="tight", facecolor="white")
    print(f"Saved {png_path}")

    puml_path = OUTPUT_DIR / "use_case_diagram.puml"
    puml_path.write_text(build_plantuml_source(), encoding="utf-8")
    print(f"Saved {puml_path}")


if __name__ == "__main__":
    main()
