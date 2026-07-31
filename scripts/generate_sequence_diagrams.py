"""Generates 4 technical UML Sequence Diagrams as PNG images.

Run with:
    python scripts/generate_sequence_diagrams.py

Produces, in docs/diagrams/:
    sequence_prediction_individuelle.png
    sequence_entrainement_automl.png
    sequence_reentrainement_auto_drift.png
    sequence_dashboard_equipements_risque.png

Each diagram reflects the actual call sequence in the codebase (controllers
-> services -> repositories/DB), not a generic textbook example. Rendered
with matplotlib only (no PlantUML/Graphviz/Java) — same reasoning as the
other diagrams, see docs/08_mlops.md.
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

EDGE = "#1e293b"
BOX_BG = "#2563eb"
ACT_BG = "#93c5fd"
NOTE_BG = "#fef9c3"
FRAME_EDGE = "#64748b"
FRAME_TAG_BG = "#e2e8f0"


class SequenceCanvas:
    """Minimal sequence-diagram drawing surface: lifelines, messages,
    activation bars, notes and alt/loop frames, laid out top-to-bottom."""

    def __init__(self, participants: list[tuple[str, str]], width: float = 20):
        self.participants = participants
        self.width = width
        n = len(participants)
        step = width / (n + 1)
        self.x = {key: step * (i + 1) for i, (key, _label) in enumerate(participants)}
        self.y = 0.0
        self.ops: list[tuple] = []
        self.active_since: dict[str, float] = {}

    def message(self, frm: str, to: str, label: str, style: str = "sync", gap: float = 1.05):
        self.ops.append(("msg", frm, to, label, style, self.y))
        self.y -= gap

    def note(self, key: str, text: str, gap: float = 0.85):
        self.ops.append(("note", key, text, self.y))
        self.y -= gap

    def activate(self, key: str):
        self.active_since[key] = self.y + 0.3

    def deactivate(self, key: str):
        if key in self.active_since:
            self.ops.append(("act", key, self.active_since.pop(key), self.y + 0.3))

    def frame_start(self, label: str, x1_key: str, x2_key: str):
        # +0.15 (not +0.5): must clear any activation bar that was just
        # deactivated right before this frame starts, or the frame's top
        # border cuts through its tail end.
        self.ops.append(("frame_start", label, self.x[x1_key] - 1.3, self.x[x2_key] + 1.3, self.y + 0.15))

    def frame_divider(self, label: str):
        self.ops.append(("frame_divider", label, self.y + 0.5))

    def frame_end(self):
        self.ops.append(("frame_end", self.y + 0.2))

    def render(self, title: str, output_path: Path):
        total_bottom = self.y - 1.0
        fig_height = max(6, (2 - total_bottom) * 0.52)
        fig, ax = plt.subplots(figsize=(self.width * 0.85, fig_height))
        ax.set_xlim(-0.5, self.width + 0.5)
        ax.set_ylim(total_bottom, 3)
        ax.axis("off")
        ax.set_title(title, fontsize=14.5, fontweight="bold", color="#0f172a", pad=14)

        box_h = 0.7
        for key, label in self.participants:
            x = self.x[key]
            box = mpatches.FancyBboxPatch(
                (x - 1.35, 2 - box_h), 2.7, box_h, boxstyle="round,pad=0.05",
                facecolor=BOX_BG, edgecolor=EDGE, linewidth=1.1, zorder=3,
            )
            ax.add_patch(box)
            ax.text(x, 2 - box_h / 2, label, ha="center", va="center", fontsize=8,
                    fontweight="bold", color="white", zorder=4)
            ax.plot([x, x], [2 - box_h, total_bottom + 0.4], linestyle="--",
                    color="#94a3b8", linewidth=1.0, zorder=1)

        frame_stack: list[tuple[str, float, float, float]] = []

        for op in self.ops:
            kind = op[0]

            if kind == "msg":
                _, frm, to, label, style, y = op
                x1, x2 = self.x[frm], self.x[to]
                color = EDGE if style != "return" else "#475569"
                ls = "--" if style == "return" else "-"

                if x1 == x2:
                    ax.plot([x1, x1 + 1.3, x1 + 1.3], [y, y, y - 0.5], color=color, linewidth=1.15, zorder=2)
                    ax.annotate("", xy=(x1, y - 0.5), xytext=(x1 + 0.06, y - 0.5),
                                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.15), zorder=2)
                    ax.text(x1 + 1.4, y - 0.24, label, fontsize=7.3, va="center", zorder=4, color=color)
                else:
                    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.15, linestyle=ls), zorder=2)
                    mx = (x1 + x2) / 2
                    ax.text(mx, y + 0.13, label, ha="center", va="bottom", fontsize=7.2, zorder=4,
                            color=color, fontstyle=("italic" if style == "return" else "normal"))

            elif kind == "note":
                _, key, text, y = op
                x = self.x[key]
                width, height = 3.6, 0.62
                box = mpatches.FancyBboxPatch(
                    (x - width / 2, y - height), width, height, boxstyle="round,pad=0.05",
                    facecolor=NOTE_BG, edgecolor="#ca8a04", linewidth=1.0, zorder=2,
                )
                ax.add_patch(box)
                ax.text(x, y - height / 2, text, ha="center", va="center", fontsize=6.9, zorder=4)

            elif kind == "act":
                _, key, y_start, y_end = op
                x = self.x[key]
                rect = mpatches.Rectangle((x - 0.12, y_end), 0.24, y_start - y_end,
                                           facecolor=ACT_BG, edgecolor=EDGE, linewidth=0.9, zorder=2)
                ax.add_patch(rect)

            elif kind == "frame_start":
                _, label, x1, x2, y_top = op
                frame_stack.append((label, x1, x2, y_top))

            elif kind == "frame_divider":
                _, label, y = op
                if frame_stack:
                    _, x1, x2, _ = frame_stack[-1]
                    ax.plot([x1, x2], [y, y], linestyle=":", color=FRAME_EDGE, linewidth=1.0, zorder=1)
                    ax.text(x1 + 0.2, y - 0.3, label, fontsize=7.2, fontweight="bold",
                            color=FRAME_EDGE, zorder=4, fontstyle="italic")

            elif kind == "frame_end":
                _, y_bottom = op
                label, x1, x2, y_top = frame_stack.pop()
                rect = mpatches.Rectangle((x1, y_bottom), x2 - x1, y_top - y_bottom,
                                           fill=False, edgecolor=FRAME_EDGE, linewidth=1.1, zorder=0)
                ax.add_patch(rect)
                tag = mpatches.Polygon(
                    [(x1, y_top), (x1 + 1.5, y_top), (x1 + 1.7, y_top - 0.4), (x1, y_top - 0.4)],
                    closed=True, facecolor=FRAME_TAG_BG, edgecolor=FRAME_EDGE, linewidth=1.0, zorder=1,
                )
                ax.add_patch(tag)
                ax.text(x1 + 0.15, y_top - 0.2, label, fontsize=7, fontweight="bold", zorder=4)

        fig.tight_layout()
        fig.savefig(output_path, dpi=165, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"Saved {output_path}")


def build_prediction_individuelle() -> None:
    participants = [
        ("user", "Utilisateur"),
        ("ctrl", "PredictionWeb\nController"),
        ("svc", "PredictionService"),
        ("fe", "FeatureEngineering\nService"),
        ("model", "Modèle ML\n(joblib)"),
        ("db", "Base de données"),
        ("notif", "Notification\nService"),
    ]
    d = SequenceCanvas(participants, width=20)

    d.message("user", "ctrl", "POST /predict (formulaire)")
    d.activate("ctrl")
    d.message("ctrl", "svc", "predict_single(payload)")
    d.activate("svc")
    d.message("svc", "svc", "valider le payload")
    d.message("svc", "db", "SELECT ModelVersion actif")
    d.message("db", "svc", "model_version", style="return")
    d.message("svc", "model", "joblib.load(file_path)")
    d.message("model", "svc", "modèle chargé", style="return")
    d.message("svc", "db", "SELECT Equipment + historique lectures")
    d.message("db", "svc", "lectures historiques", style="return")
    d.message("svc", "fe", "engineer_features(df)")
    d.activate("fe")
    d.message("fe", "svc", "DataFrame enrichi (57 variables)", style="return")
    d.deactivate("fe")
    d.message("svc", "model", "predict_proba(X)")
    d.message("model", "svc", "probabilité", style="return")
    d.message("svc", "svc", "calculer risk_level")
    d.message("svc", "db", "INSERT Prediction")
    d.message("svc", "ctrl", "résultat {probability, risk_level, ...}", style="return")
    d.deactivate("svc")

    d.frame_start("alt  [risque == Critical ou High]", "ctrl", "notif")
    d.message("ctrl", "notif", "notify_critical_predictions([résultat])")
    d.message("notif", "db", "INSERT Notification")
    d.frame_end()

    d.message("ctrl", "user", "page HTML avec résultat", style="return")
    d.deactivate("ctrl")

    d.render(
        "Diagramme de Séquence — Lancer une prédiction individuelle",
        OUTPUT_DIR / "sequence_prediction_individuelle.png",
    )


def build_entrainement_automl() -> None:
    participants = [
        ("ds", "Data Scientist\n(CLI)"),
        ("pipe", "train_pipeline"),
        ("svc", "TrainingService"),
        ("fe", "FeatureEngineering\nService"),
        ("optuna", "OptunaTuner"),
        ("reg", "ModelRegistry\nService"),
        ("fs", "Base de données /\nFichiers"),
    ]
    d = SequenceCanvas(participants, width=20)

    d.message("ds", "pipe", "python -m app.ml.training.train_pipeline")
    d.activate("pipe")
    d.message("pipe", "svc", "prepare_dataset()")
    d.activate("svc")
    d.message("svc", "svc", "charger + nettoyer les données")
    d.message("svc", "fe", "engineer_features(df)")
    d.activate("fe")
    d.message("fe", "svc", "57 variables dérivées", style="return")
    d.deactivate("fe")
    d.message("svc", "pipe", "dataset préparé", style="return")
    d.deactivate("svc")

    d.note("pipe", "Diagnostic du signal :\nmutual_info_classif(capteurs, cible)")

    d.message("pipe", "svc", "split_and_resample()  [SMOTE]")
    d.message("svc", "pipe", "X_train / X_test / y_train / y_test", style="return")

    d.frame_start("loop  [7 familles de modèles]", "pipe", "svc")
    d.message("pipe", "svc", "run_baseline_comparison(...)")
    d.message("svc", "svc", "fit() + evaluate() par modèle")
    d.frame_end()
    d.message("svc", "pipe", "leaderboard baseline", style="return")

    d.frame_start("loop  [top 3 modèles du classement]", "pipe", "optuna")
    d.message("pipe", "optuna", "tune_model(name, n_trials=30)")
    d.activate("optuna")
    d.message("optuna", "optuna", "cross_val_score × 30 essais")
    d.message("optuna", "pipe", "meilleurs hyperparamètres", style="return")
    d.deactivate("optuna")
    d.frame_end()

    d.message("pipe", "pipe", "sélectionner le meilleur modèle\n(score composite F1/ROC AUC)")
    d.message("pipe", "reg", "register_best_model(model, metrics, ...)")
    d.activate("reg")
    d.message("reg", "fs", "joblib.dump(model) + feature_list.json")
    d.message("reg", "fs", "INSERT ModelVersion + TrainingRun\n(désactive l'ancien)")
    d.message("reg", "pipe", "model_version", style="return")
    d.deactivate("reg")
    d.message("pipe", "ds", "leaderboard + modèle retenu (console)", style="return")
    d.deactivate("pipe")

    d.render(
        "Diagramme de Séquence — Entraîner le modèle (AutoML + Optuna)",
        OUTPUT_DIR / "sequence_entrainement_automl.png",
    )


def build_reentrainement_auto() -> None:
    participants = [
        ("sched", "Planificateur\n(cron / Task Scheduler)"),
        ("auto", "auto_retrain"),
        ("drift", "DriftService"),
        ("db", "Base de données"),
        ("pipe", "train_pipeline\n(voir diagramme 2)"),
    ]
    d = SequenceCanvas(participants, width=17)

    d.message("sched", "auto", "python -m app.ml.training.auto_retrain\n(déclenchement quotidien)")
    d.activate("auto")
    d.message("auto", "drift", "detect_drift()")
    d.activate("drift")
    d.message("drift", "db", "SELECT lectures (triées par date)")
    d.message("db", "drift", "historique des lectures", style="return")
    d.message("drift", "drift", "calculer PSI + test de\nKolmogorov-Smirnov par capteur")
    d.message("drift", "auto", "rapport {status, features}", style="return")
    d.deactivate("drift")

    d.frame_start("alt  [status == stable]", "auto", "pipe")
    d.message("auto", "sched", "log : « aucune dérive détectée »", style="return")
    d.frame_divider("else  [status == drift_detected]")
    d.message("auto", "pipe", "run()")
    d.activate("pipe")
    d.message("pipe", "auto", "nouveau modèle actif enregistré", style="return")
    d.deactivate("pipe")
    d.message("auto", "sched", "log : « réentraînement effectué,\nnouveau modèle actif »", style="return")
    d.frame_end()
    d.deactivate("auto")

    d.render(
        "Diagramme de Séquence — Réentraînement automatique (déclenché par Data Drift)",
        OUTPUT_DIR / "sequence_reentrainement_auto_drift.png",
    )


def build_dashboard_equipements_risque() -> None:
    participants = [
        ("user", "Utilisateur"),
        ("browser", "Navigateur (JS)"),
        ("dctrl", "Dashboard /\nEquipment Controller"),
        ("dsvc", "Dashboard /\nEquipment Service"),
        ("db", "Base de données"),
    ]
    d = SequenceCanvas(participants, width=17)

    d.frame_start("Phase 1 — Consulter le tableau de bord (KPIs)", "user", "db")
    d.message("user", "browser", "ouvre « / »")
    d.message("browser", "dctrl", "GET /")
    d.message("dctrl", "browser", "HTML (structure + script JS)", style="return")
    d.message("browser", "dctrl", "GET /dashboard/api/data (fetch au chargement)")
    d.activate("dctrl")
    d.message("dctrl", "dsvc", "get_full_dashboard_payload()")
    d.activate("dsvc")
    d.message("dsvc", "db", "KPIs : équipements, pannes, MTBF, MTTR, ...")
    d.message("db", "dsvc", "résultats agrégés", style="return")
    d.message("dsvc", "db", "failures_by_type, top_critical,\névolution mensuelle, dernières activités")
    d.message("db", "dsvc", "séries pour les graphiques", style="return")
    d.message("dsvc", "dctrl", "payload JSON", style="return")
    d.deactivate("dsvc")
    d.message("dctrl", "browser", "JSON", style="return")
    d.deactivate("dctrl")
    d.message("browser", "browser", "rendu Chart.js / ApexCharts")
    d.frame_end()

    d.frame_start("Phase 2 — Consulter les équipements à risque", "user", "db")
    d.message("user", "browser", "clique « Équipements à risque »")
    d.message("browser", "dctrl", "GET /equipment/at-risk")
    d.activate("dctrl")
    d.message("dctrl", "dsvc", "get_latest_predictions_ranked()")
    d.activate("dsvc")
    d.message("dsvc", "db", "dernière Prediction par équipement\nJOIN Equipment, ORDER BY probability DESC")
    d.message("db", "dsvc", "liste classée", style="return")
    d.message("dsvc", "dctrl", "équipements à risque (classés)", style="return")
    d.deactivate("dsvc")
    d.message("dctrl", "browser", "page HTML (tableau classé)", style="return")
    d.deactivate("dctrl")
    d.frame_end()

    d.render(
        "Diagramme de Séquence — Tableau de bord (KPIs) & Équipements à risque",
        OUTPUT_DIR / "sequence_dashboard_equipements_risque.png",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_prediction_individuelle()
    build_entrainement_automl()
    build_reentrainement_auto()
    build_dashboard_equipements_risque()


if __name__ == "__main__":
    main()
