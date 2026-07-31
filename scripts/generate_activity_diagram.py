"""Generates the UML Activity Diagram (main business flow) as a PNG image.

Run with:
    python scripts/generate_activity_diagram.py

Produces docs/diagrams/activity_diagram.png — end-to-end flow from login to
a maintenance action, covering the core "predict which equipment will fail"
loop that is the heart of the system (login -> fleet prediction -> risk
ranking -> explanation -> maintenance action).

Rendered with matplotlib only (no Graphviz/PlantUML/Java dependency) for the
same reason as the use case diagram — see docs/08_mlops.md.
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

USER_COLOR = "#dbeafe"
SYSTEM_COLOR = "#dcfce7"
DECISION_COLOR = "#fef3c7"
END_ALT_COLOR = "#fee2e2"
EDGE_COLOR = "#334155"


def draw_start(ax, x, y):
    ax.add_patch(mpatches.Circle((x, y), 0.35, facecolor="black", zorder=2))


def draw_end(ax, x, y):
    ax.add_patch(mpatches.Circle((x, y), 0.42, facecolor="white", edgecolor="black", linewidth=1.6, zorder=2))
    ax.add_patch(mpatches.Circle((x, y), 0.22, facecolor="black", zorder=2))


def draw_action(ax, x, y, text, color, width=5.6, height=1.5):
    box = mpatches.FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.08,rounding_size=0.35",
        facecolor=color, edgecolor=EDGE_COLOR, linewidth=1.1, zorder=2,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=8.4, color="#0f172a", zorder=3)
    return (x, y - height / 2), (x, y + height / 2), (x - width / 2, y), (x + width / 2, y)


def draw_decision(ax, x, y, text, size=1.75):
    # numVertices=4 with orientation=0 already places vertices at
    # top/left/bottom/right, i.e. a diamond — do not rotate further.
    diamond = mpatches.RegularPolygon(
        (x, y), numVertices=4, radius=size, orientation=0,
        facecolor=DECISION_COLOR, edgecolor=EDGE_COLOR, linewidth=1.1, zorder=2,
    )
    ax.add_patch(diamond)
    ax.text(x, y, text, ha="center", va="center", fontsize=7.8, color="#0f172a", zorder=3)
    return (x, y - size), (x, y + size), (x - size, y), (x + size, y)


def arrow(ax, p1, p2, label=None, color=EDGE_COLOR, connectionstyle="arc3,rad=0.0"):
    ax.annotate(
        "", xy=p2, xytext=p1,
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3, connectionstyle=connectionstyle),
        zorder=1,
    )
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx + 0.35, my, label, fontsize=7.6, color="#b45309", fontstyle="italic", zorder=4)


def build_diagram() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(15, 23))
    ax.set_xlim(-2, 20)
    ax.set_ylim(-3, 47)
    ax.axis("off")
    ax.set_title(
        "Diagramme d'Activité — Prédiction de panne et action de maintenance",
        fontsize=15, fontweight="bold", color="#0f172a", pad=16,
    )

    cx = 8  # main spine x

    # --- Spine coordinates (top to bottom) ---------------------------------
    # Gaps between consecutive centers are sized as (half-size1 + half-size2
    # + buffer) so diamond tips (radius 1.75) never overlap adjacent nodes.
    y_start = 45
    y_login = 43
    y_d1 = 39.6
    y_dashboard = 36.2
    y_navigate = 33.8
    y_d2 = 30.4
    y_launch = 27.0
    y_load = 24.6
    y_features = 22.2
    y_predict = 19.8
    y_persist = 17.4
    y_display = 15.0
    y_d3 = 11.6
    y_d4 = 7.2
    y_maint = 3.8
    y_status = 1.4
    y_end = -0.7

    draw_start(ax, cx, y_start)
    b_login = draw_action(ax, cx, y_login, "Se connecter\n(saisir identifiants)", USER_COLOR)
    d1 = draw_decision(ax, cx, y_d1, "Authentification\nvalide ?")

    # non -> error -> loop back to login
    err_x = 2.5
    b_err = draw_action(ax, err_x, y_d1, "Afficher message\nd'erreur", END_ALT_COLOR, width=4.4, height=1.4)
    arrow(ax, d1[2], (err_x + 2.2, y_d1), "non")
    arrow(ax, (err_x, y_d1 + 0.7), (cx - 1.2, y_login), connectionstyle="arc3,rad=-0.3")

    b_dash = draw_action(ax, cx, y_dashboard, "Accéder au tableau\nde bord", USER_COLOR)
    arrow(ax, d1[1], b_dash[1], "oui")
    arrow(ax, b_login[0], d1[1])

    b_nav = draw_action(ax, cx, y_navigate, "Naviguer vers\n« Équipements à risque »", USER_COLOR)
    arrow(ax, b_dash[0], b_nav[1])

    d2 = draw_decision(ax, cx, y_d2, "Modèle actif\ndisponible ?")
    arrow(ax, b_nav[0], d2[1])

    # non -> no model message -> alternate end
    nomodel_x = 2.5
    b_nomodel = draw_action(ax, nomodel_x, y_d2, "Afficher « Aucun\nmodèle actif »", END_ALT_COLOR, width=4.4, height=1.5)
    arrow(ax, d2[2], (nomodel_x + 2.2, y_d2), "non")
    end_alt_y = y_d2 - 3.4
    draw_end(ax, nomodel_x, end_alt_y)
    arrow(ax, (nomodel_x, y_d2 - 0.75), (nomodel_x, end_alt_y + 0.45))

    b_launch = draw_action(ax, cx, y_launch, "Lancer la prédiction\nsur toute la flotte", USER_COLOR)
    arrow(ax, d2[1], b_launch[1], "oui")

    b_load = draw_action(ax, cx, y_load, "Système : charger le modèle actif\n+ historique des lectures", SYSTEM_COLOR)
    arrow(ax, b_launch[0], b_load[1])

    b_feat = draw_action(ax, cx, y_features, "Système : calculer les\ncaractéristiques (feature engineering)", SYSTEM_COLOR)
    arrow(ax, b_load[0], b_feat[1])

    b_predict = draw_action(ax, cx, y_predict, "Système : prédire la probabilité\nde panne par équipement", SYSTEM_COLOR)
    arrow(ax, b_feat[0], b_predict[1])

    b_persist = draw_action(ax, cx, y_persist, "Système : enregistrer les prédictions\n+ générer les alertes critiques", SYSTEM_COLOR)
    arrow(ax, b_predict[0], b_persist[1])

    b_display = draw_action(ax, cx, y_display, "Afficher le classement des\néquipements à risque", USER_COLOR)
    arrow(ax, b_persist[0], b_display[1])

    d3 = draw_decision(ax, cx, y_d3, "Consulter\nl'explicabilité ?")
    arrow(ax, b_display[0], d3[1])

    shap_x = 14.5
    b_shap = draw_action(ax, shap_x, y_d3, "Afficher l'explication SHAP\n(facteurs de risque + recommandation)", SYSTEM_COLOR, width=5.6, height=1.7)
    arrow(ax, d3[3], (shap_x - 2.8, y_d3), "oui")

    d4 = draw_decision(ax, cx, y_d4, "Risque élevé\nconfirmé ?")
    arrow(ax, d3[0], d4[1], "non")
    arrow(ax, (shap_x, y_d3 - 0.85), (cx + 1.3, y_d4 + 0.9), connectionstyle="arc3,rad=0.25")

    b_maint = draw_action(ax, cx, y_maint, "Enregistrer une intervention\nde maintenance", USER_COLOR)
    arrow(ax, d4[0], b_maint[1], "oui")

    b_status = draw_action(ax, cx, y_status, "Mettre à jour le statut\nde l'équipement", SYSTEM_COLOR)
    arrow(ax, b_maint[0], b_status[1])

    draw_end(ax, cx, y_end)
    arrow(ax, b_status[0], (cx, y_end + 0.45))

    # non -> directly to end (clean L-shaped path: left, down, right)
    bypass_x = cx - 3.6
    arrow(ax, d4[2], (bypass_x, y_d4), "non")
    ax.plot([bypass_x, bypass_x], [y_d4, y_end], color=EDGE_COLOR, linewidth=1.3, zorder=1)
    arrow(ax, (bypass_x, y_end), (cx - 0.5, y_end))

    # --- Legend --------------------------------------------------------------
    legend_items = [
        mpatches.Patch(facecolor=USER_COLOR, edgecolor=EDGE_COLOR, label="Action utilisateur"),
        mpatches.Patch(facecolor=SYSTEM_COLOR, edgecolor=EDGE_COLOR, label="Action système / ML"),
        mpatches.Patch(facecolor=DECISION_COLOR, edgecolor=EDGE_COLOR, label="Décision"),
        mpatches.Patch(facecolor=END_ALT_COLOR, edgecolor=EDGE_COLOR, label="Chemin alternatif"),
    ]
    ax.legend(handles=legend_items, loc="upper right", frameon=True, fontsize=8.5)

    fig.tight_layout()
    return fig


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = build_diagram()
    output_path = OUTPUT_DIR / "activity_diagram.png"
    fig.savefig(output_path, dpi=170, bbox_inches="tight", facecolor="white")
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
