# Rapport de Collecte des Données

## Objectif

Mettre en place un module de collecte de données capable d'ingérer les lectures de capteurs
des équipements miniers lourds (Heavy Mobile Equipment) depuis plusieurs sources, de valider
automatiquement leur structure, et de produire un rapport de qualité avant tout traitement en aval.

## Méthodes utilisées

- **Détection automatique des colonnes** : `DataLoaderService` (app/services/data/data_loader_service.py)
  charge le classeur Excel source (`Datasets/Synthetic_Datasets_10_Master_Projects_10000Rows.xlsx`,
  feuille `1_HME_Downtime`) et valide par nom (pas par position) que les 9 colonnes attendues
  (EquipmentID, EquipmentType, Timestamp, OperatingHours, EngineTemp, HydraulicPressure,
  Vibration, FailureMode, FailureWithin7Days) sont présentes, avec une erreur explicite sinon.
- **Formats supportés** : Excel (.xlsx, implémenté et utilisé en production dans ce projet) et
  CSV (implémenté dans le module de prédiction par lot, `prediction_web_controller.handle_batch`,
  qui accepte un import CSV de lectures pour scoring en masse).
- **Connecteurs bases de données** : l'architecture en couches (DataLoaderService isolé derrière
  une interface simple `load() -> DataFrame`) permet de brancher un connecteur PostgreSQL ou
  SQL Server (via SQLAlchemy `create_engine` + `pd.read_sql`) sans modifier le reste du pipeline —
  seule l'implémentation de `DataLoaderService.load()` changerait. Ce connecteur n'a pas été
  implémenté concrètement faute d'instance PostgreSQL/SQL Server disponible dans l'environnement
  de développement, mais l'interface est prête à l'accueillir.
- **Vérification de qualité** : `DataCleaningService` détecte les doublons (clé EquipmentID +
  Timestamp), vérifie les types de données, et l'`EdaService` calcule automatiquement le nombre
  de valeurs manquantes par colonne.

## Résultats obtenus

Sur le fichier fourni : 10 000 lignes, 9 colonnes, **1 doublon détecté et supprimé**, **0 valeur
manquante** sur l'ensemble des colonnes, tous les types de données conformes après coercition
(Timestamp → datetime, identifiants → string).

## Avantages

- Détection par nom de colonne : robuste aux réordonnancements du fichier source.
- Échec rapide et explicite (`ValueError`) si une colonne attendue disparaît, plutôt qu'une
  erreur silencieuse plus loin dans le pipeline.
- Architecture découplée : le reste du système (nettoyage, feature engineering, entraînement)
  ne connaît jamais la source physique des données.

## Limites

- Les connecteurs PostgreSQL/SQL Server sont conçus mais non implémentés/testés (absence
  d'instance disponible) — à finaliser avant un déploiement multi-sources réel.
- Le rapport de qualité actuel est calculé à la demande (page EDA) plutôt que persisté comme
  artefact versionné à chaque ingestion — une amélioration MLOps naturelle serait de le stocker
  en base (table `Report`) à chaque import.
