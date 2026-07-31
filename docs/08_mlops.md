# Rapport MLOps

## Objectif

Fournir un socle MLOps qui couvre le cycle de vie du modèle (registre, versioning,
monitoring, détection de dérive, réentraînement) en ne livrant que ce qui peut être
réellement exécuté et vérifié dans l'environnement de développement de ce projet — plutôt
que de générer des fichiers de configuration Airflow/Kedro/MinIO non testés qui donneraient
une fausse impression de fonctionnement.

## Méthodes utilisées

| Besoin MLOps | Outil demandé | Implémentation réelle dans ce projet |
|---|---|---|
| Registre de modèles | — | Table `ModelVersion` + fichiers `.joblib`/`.json` dans `app/ml/artifacts/` (`ModelRegistryService`) |
| Versioning des modèles | — | `version_number` horodaté, un seul modèle `is_active=True` à la fois, historique consultable dans Administration |
| Historique d'entraînement | — | Table `TrainingRun` (leaderboard complet en JSON, notes de diagnostic) |
| Monitoring / logging | — | `app/utils/logger.py` (fichier + console), `AuditLog` pour les actions utilisateurs |
| Détection de Data Drift | Airflow + Evidently (implicite) | `DriftService` : PSI + test de Kolmogorov-Smirnov par capteur, page `/admin/drift` |
| Détection de Concept Drift | — | Non implémenté (nécessite un flux de vraies étiquettes en continu, absent ici) — voir Limites |
| Réentraînement automatique | Airflow (orchestrateur) | `python -m app.ml.training.auto_retrain` : vérifie la dérive puis relance `train_pipeline` si nécessaire |
| Orchestration planifiée | Airflow | Documentée ci-dessous via le Planificateur de tâches Windows / cron (pas de DAG Airflow — aucun serveur Airflow disponible dans cet environnement) |
| Conteneurisation | Docker | `Dockerfile` (Flask), `Dockerfile.api` (FastAPI), `docker-compose.yml` — **fournis mais non construits/exécutés ici** (pas de démon Docker dans le sandbox de développement) |
| Stockage objet des modèles/données | MinIO | Non implémenté — les artefacts restent sur disque local (`app/ml/artifacts/`), suffisant pour un déploiement mono-serveur ; un stockage S3/MinIO serait un simple changement de `ModelRegistryService.artifacts_dir` vers un client `boto3` |
| API de prédiction | FastAPI | `app/api_fastapi/` — implémenté, testé, remplace l'ancienne API Flask (voir `run_api.py`) |
| Dashboard Data Science | Streamlit | Non implémenté séparément — le rôle est couvert par les pages Flask `/eda`, `/feature-selection`, `/evaluation`, `/explainability`, qui sont déjà interactives (Plotly) et intégrées à l'authentification/rôles existants ; ajouter un Streamlit dédié dupliquerait cette logique sans bénéfice net ici |

### Planification du réentraînement sans Airflow

```
# Windows Task Scheduler (via schtasks), tous les jours à 02h00 :
schtasks /create /tn "HME_AutoRetrain" /tr "C:\...\.venv\Scripts\python.exe -m app.ml.training.auto_retrain" /sc daily /st 02:00

# Linux/macOS cron, tous les jours à 02h00 :
0 2 * * * /path/to/.venv/bin/python -m app.ml.training.auto_retrain
```

## Résultats obtenus

`DriftService.detect_drift()` fonctionne de bout en bout sur les données seedées (PSI et
KS-test calculés par capteur, statut `stable`/`drift_detected` renvoyé). Le registre de
modèles et l'historique d'entraînement sont peuplés et consultables. Le service FastAPI a été
testé (login JWT, prédiction, prédiction de flotte, CRUD équipement — voir
`tests/integration/test_fastapi_service.py`).

## Avantages

- Tout ce qui est documenté comme "fonctionnel" a été exécuté et vérifié dans ce projet — pas
  de configuration MLOps décorative non testée.
- Le chemin d'évolution vers Airflow/MinIO/Kedro est explicite (tableau ci-dessus) : aucune
  réécriture d'architecture ne serait nécessaire, seulement un changement d'implémentation
  derrière des interfaces déjà découplées (`DataLoaderService`, `ModelRegistryService`).

## Limites

- Pas d'orchestrateur Airflow réel : la "planification" repose sur le scheduler de l'OS, ce
  qui suffit pour un seul job quotidien mais ne offrirait pas de vue DAG multi-étapes ni de
  reprise sur erreur avancée qu'Airflow fournirait.
- Pas de détection de Concept Drift (dérive de la relation features→cible) : elle nécessite
  de comparer les performances du modèle sur de nouvelles étiquettes réelles au fil du temps,
  un flux qui n'existe pas avec un dataset statique importé une fois.
- Docker/MinIO/Kedro/Streamlit ne sont pas exécutés dans cet environnement de développement
  (pas de démon Docker disponible) — à valider par l'utilisateur sur sa propre machine avant
  toute démonstration s'appuyant dessus.
