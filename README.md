# Intelligent Heavy Mobile Equipment Predictive Maintenance System

> Système intelligent de maintenance prédictive pour équipements miniers lourds (excavatrices,
> chargeuses, foreuses, camions, niveleuses, bulldozers), fondé sur le Machine Learning, l'IA
> explicable (XAI) et les pratiques MLOps.
>
> Projet académique — Mémoire de Master en Informatique / Génie Logiciel / Science des Données.

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.7-F7931E?logo=scikit-learn&logoColor=white)
![Tests](https://img.shields.io/badge/tests-14%20passed-brightgreen)
![Status](https://img.shields.io/badge/status-academic%20project-lightgrey)

---

## Table des matières

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Stack technique](#stack-technique)
- [Architecture](#architecture)
- [Structure du projet](#structure-du-projet)
- [Installation](#installation)
- [Démarrage](#démarrage)
- [Comptes de démonstration](#comptes-de-démonstration)
- [Tests](#tests)
- [Documentation](#documentation)
- [Limites connues](#limites-connues)
- [Feuille de route](#feuille-de-route)
- [Licence](#licence)

---

## Aperçu

Ce projet met en œuvre une chaîne complète de maintenance prédictive pour équipements miniers
lourds (HME) : collecte et nettoyage des données capteurs, ingénierie de 57 variables dérivées,
comparaison automatisée (AutoML) de 7 familles de modèles, optimisation des hyperparamètres
(Optuna), explicabilité des prédictions (SHAP), tableau de bord interactif, API REST sécurisée et
mécanismes légers de MLOps (registre de modèles, détection de dérive des données, réentraînement
automatique).

Le système est organisé en deux services indépendants partageant la même base de données et les
mêmes modèles :

| Service | Rôle | Port |
|---|---|---|
| **Flask** (`run.py`) | Interface web complète (dashboard, équipements, prédiction, explicabilité, rapports, administration) | 5000 |
| **FastAPI** (`run_api.py`) | API REST publique (JWT), pour intégrations tierces — documentation Swagger auto-générée | 8000 |

## Fonctionnalités

**Web & Dashboard**
- Authentification par session (Flask-Login, bcrypt), 4 rôles (Admin, Ingénieur, Technicien, Manager)
- Tableau de bord temps réel : disponibilité, MTBF, MTTR, pannes, équipements critiques
- Gestion des équipements (CRUD), historique de maintenance, notifications automatiques

**Machine Learning**
- Pipeline AutoML comparant Random Forest, Extra Trees, Gradient Boosting, HistGradientBoosting,
  XGBoost, LightGBM et CatBoost
- Optimisation bayésienne des hyperparamètres (Optuna, 30 essais) sur le top 3
- 57 variables dérivées automatiquement (scores de risque, tendances temporelles, interactions)
- Rééquilibrage SMOTE, registre de modèles versionné, sélection automatique du meilleur modèle
- **Prédiction individuelle**, **par lot (CSV)** et **sur toute la flotte** (classement des
  équipements à risque)

**Explicabilité & Science des données**
- Explicabilité SHAP (Summary, Waterfall, Dependence Plot) + narration en langage naturel
- Page d'analyse exploratoire (EDA) interactive (Plotly) avec export PDF
- Comparaison de 6 méthodes de sélection de variables (Mutual Information, RFE, Permutation
  Importance, SHAP, Variance Threshold, Boruta)
- Évaluation avancée : ROC, Precision-Recall, calibration, lift/gain, learning curve, Cohen's Kappa

**MLOps & Sécurité**
- Détection de dérive des données (PSI + test de Kolmogorov-Smirnov) et réentraînement automatique
- API REST sécurisée par JWT (FastAPI, Swagger/OpenAPI)
- CSRF (Flask-WTF), rate limiting (Flask-Limiter), journal d'audit, panneau d'administration
- Export de rapports (CSV, Excel, PDF) et documentation scientifique générée automatiquement

## Stack technique

| Domaine | Technologies |
|---|---|
| Backend web | Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter |
| API REST | FastAPI, Pydantic, Uvicorn, PyJWT |
| Base de données | SQLite (SQLAlchemy ORM, 12 modèles relationnels) |
| Machine Learning | scikit-learn, XGBoost, LightGBM, CatBoost, imbalanced-learn (SMOTE), Optuna |
| Explicabilité | SHAP, Boruta |
| Visualisation | Chart.js, ApexCharts, Plotly, Bootstrap 5 |
| Rapports & docs | ReportLab (PDF), python-docx (Word), python-pptx (PowerPoint), openpyxl |
| Tests | pytest, pytest-cov |
| Déploiement | Docker, docker-compose (fournis, non validés — voir [Limites connues](#limites-connues)) |

## Architecture

Architecture en couches (MVC + services + repositories) :

```
Interface Web (Flask)  →  Services métier  →  Repositories  →  Base de données (SQLite)
                              ↓
API REST (FastAPI, JWT)  ←────┘
                              ↓
                    Machine Learning (AutoML, Optuna, SHAP, Registre de modèles)
```

Les diagrammes UML complets (cas d'utilisation, classes, activité, séquence) sont disponibles dans
[`docs/diagrams/`](docs/diagrams/).

## Structure du projet

```
Equipement/
├── app/
│   ├── api_fastapi/        # Service FastAPI (API REST publique, JWT, Swagger)
│   ├── config/              # Configuration (Dev/Test/Prod)
│   ├── controllers/          # Contrôleurs Flask (blueprints)
│   ├── database/             # Seed de la base de données
│   ├── extensions.py         # Extensions Flask partagées
│   ├── ml/
│   │   ├── training/          # Pipeline d'entraînement AutoML + réentraînement auto
│   │   └── artifacts/         # Modèles entraînés (.joblib, feature_list.json)
│   ├── models/                # Modèles SQLAlchemy (12 tables)
│   ├── repositories/          # Couche d'accès aux données
│   ├── routes/                # Enregistrement des blueprints
│   ├── services/              # Logique métier (data, ml, dashboard, equipment, reports...)
│   └── utils/                 # Logger, constantes, décorateurs, validateurs
├── Datasets/                  # Jeu de données source (Excel)
├── docs/
│   ├── 01...08_*.md           # Documentation scientifique par étape (données, ML, MLOps...)
│   ├── diagrams/               # 9 diagrammes UML (PNG)
│   ├── report_assets/          # Graphiques et statistiques réels (EDA, SHAP, feature importance)
│   ├── rapport_scientifique_HME.docx   # Mémoire complet (IMRAD)
│   └── soutenance_HME.pptx     # Présentation de soutenance (17 diapositives)
├── scripts/                   # Scripts de génération (diagrammes, rapport, présentation)
├── static/ & templates/        # Frontend Flask (CSS, JS, Jinja2)
├── tests/                     # Tests unitaires et d'intégration (pytest)
├── docker-compose.yml, Dockerfile, Dockerfile.api
├── requirements.txt
├── run.py                     # Point d'entrée Flask (port 5000)
└── run_api.py                 # Point d'entrée FastAPI (port 8000)
```

## Installation

**Prérequis** : Python 3.10+

```bash
# 1. Cloner le dépôt
git clone <url-du-depot>
cd Equipement

# 2. Créer et activer un environnement virtuel
python -m venv .venv
# Windows :
.venv\Scripts\Activate.ps1
# Linux/macOS :
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Copier la configuration
cp .env.example .env
```

Le jeu de données source doit se trouver dans `Datasets/` (déjà présent dans ce dépôt : fichier
Excel, feuille `1_HME_Downtime`).

## Démarrage

```bash
# 1. Initialiser la base de données et importer le dataset (idempotent)
python -m app.database.seed

# 2. Entraîner le modèle (AutoML + Optuna) — nécessaire avant toute prédiction
python -m app.ml.training.train_pipeline

# 3a. Lancer l'application web (Flask)
python run.py
# → http://127.0.0.1:5000

# 3b. Lancer l'API REST (FastAPI), dans un autre terminal
python run_api.py
# → http://127.0.0.1:8000/docs (Swagger)
```

**Réentraînement automatique** (déclenché en cas de dérive des données), à planifier via le
planificateur de tâches de l'OS :

```bash
python -m app.ml.training.auto_retrain
```

## Comptes de démonstration

| Utilisateur | Mot de passe | Rôle |
|---|---|---|
| `admin` | `Admin@123` | Administrateur |
| `ingenieur` | `Ingenieur@123` | Ingénieur |
| `technicien` | `Technicien@123` | Technicien |
| `manager` | `Manager@123` | Manager |

> Créés automatiquement par `python -m app.database.seed`. À changer avant tout déploiement réel.

## Tests

```bash
pytest tests/ -v
```

14 tests (unitaires + intégration) couvrant le feature engineering, l'AutoML, l'authentification,
les routes équipements et l'API FastAPI.

## Documentation

| Document | Description |
|---|---|
| [`docs/rapport_scientifique_HME.docx`](docs/rapport_scientifique_HME.docx) | Mémoire scientifique complet (structure IMRAD, ~30 pages) |
| [`docs/soutenance_HME.pptx`](docs/soutenance_HME.pptx) | Présentation de soutenance (17 diapositives) |
| [`docs/diagrams/`](docs/diagrams/) | 9 diagrammes UML (cas d'utilisation, classes, activité, 4 séquences) |
| [`docs/01_data_collection.md`](docs/01_data_collection.md) → [`08_mlops.md`](docs/08_mlops.md) | Documentation scientifique par étape (objectif, méthodes, résultats, limites) |
| [`docs/exports/`](docs/exports/) | Documentation ci-dessus exportée en PDF / Word / HTML |

Régénérer les livrables :

```bash
python scripts/generate_report_assets.py      # graphiques + statistiques réelles
python scripts/generate_word_report.py        # rapport .docx
python scripts/generate_presentation.py       # présentation .pptx
python scripts/generate_use_case_diagram.py   # + generate_class_diagram.py, generate_activity_diagram.py, generate_sequence_diagrams.py
python scripts/export_documentation.py        # docs/*.md → PDF/Word/HTML
```

## Limites connues

- **Signal du dataset** : l'analyse statistique (corrélation, information mutuelle, SHAP) montre
  une absence de relation exploitable entre les capteurs bruts et la variable cible dans le jeu de
  données synthétique fourni (ROC AUC ≈ 0,51). Le pipeline est entièrement fonctionnel ; c'est une
  limite du dataset de démonstration, documentée en détail dans
  [`docs/03_eda.md`](docs/03_eda.md) et dans le rapport scientifique.
- **Docker** : `Dockerfile`, `Dockerfile.api` et `docker-compose.yml` sont fournis mais n'ont pas pu
  être construits/exécutés dans l'environnement de développement (aucun démon Docker disponible).
  À valider avant tout déploiement.
- **Concept drift** : non implémenté (nécessiterait un flux continu d'étiquettes réelles).

## Feuille de route

- [ ] Reconnecter le pipeline à un flux de données réel (historien industriel / SCADA)
- [ ] Connecteurs PostgreSQL / SQL Server (interface déjà prête dans `DataLoaderService`)
- [ ] Validation du déploiement conteneurisé (Docker Compose)
- [ ] Détection de concept drift (dérive de la relation features → cible)

## Licence

Projet académique réalisé dans le cadre d'un mémoire de Master. Licence à définir par l'auteur
avant publication ou réutilisation.

---

*Développé comme démonstrateur pour un usage type entreprise minière (Kamoa Copper, Tenke
Fungurume Mining, MMG Kinsevere, Ivanhoe Mines, Glencore, CMOC).*
