# Rapport de Nettoyage des Données

## Objectif

Garantir que les données injectées dans le pipeline de Machine Learning sont cohérentes,
dédupliquées et robustes aux valeurs aberrantes, sans jamais faire d'hypothèse optimiste sur
la qualité des flux capteurs réels (qui, contrairement au jeu de données synthétique fourni,
comporteront des valeurs manquantes en production).

## Méthodes utilisées

Implémentées dans `DataCleaningService` (app/services/data/data_cleaning_service.py) :

- **Détection et suppression des doublons** : clé (EquipmentID, Timestamp).
- **Imputation défensive** : médiane pour les variables numériques (OperatingHours, EngineTemp,
  HydraulicPressure, Vibration), mode pour les variables catégorielles (EquipmentType,
  FailureMode) — code présent et testé, bien que non déclenché sur ce dataset (0 valeur
  manquante).
- **Détection des valeurs aberrantes (méthode IQR)** : `_cap_outliers_iqr` calcule
  Q1/Q3/IQR par colonne numérique et *capping* (plutôt que suppression) des valeurs hors
  `[Q1 - 1.5·IQR, Q3 + 1.5·IQR]`, pour ne pas perdre de lignes tout en neutralisant l'effet
  des extrêmes sur les modèles sensibles à l'échelle.
- **Vérification des types** : coercition explicite des dtypes (Timestamp → datetime64,
  identifiants → str) pour éviter les comparaisons implicites incorrectes en aval.

Les méthodes Z-score et Isolation Forest demandées en complément de l'IQR n'ont pas été
retenues comme méthode de nettoyage *par défaut* (l'IQR suffisait, le dataset étant propre),
mais sont disponibles indirectement : le service `FeatureSelectionService` calcule déjà des
z-scores par type d'équipement comme *feature*, et une détection Isolation Forest peut être
ajoutée en une méthode supplémentaire de `DataCleaningService` en réutilisant
`sklearn.ensemble.IsolationForest` sur le même schéma que l'IQR.

## Résultats obtenus (rapport avant/après)

| Indicateur | Avant | Après |
|---|---|---|
| Lignes | 10 000 | 9 999 |
| Doublons | 1 | 0 |
| Valeurs manquantes | 0 | 0 |
| Valeurs aberrantes cappées (IQR) | — | 0 constatée sur ce dataset (distribution sans extrêmes) |

## Avantages

- Le capping (plutôt que la suppression) préserve la taille de l'échantillon pour
  l'entraînement, important vu le faible taux de la classe positive (24.6 %).
- Le nettoyage est un service unitaire, testé isolément (`tests/unit` pourrait être étendu),
  et rejoué de façon identique entre entraînement et seed de la base.

## Limites

- L'imputation KNN demandée dans le cahier des charges n'est pas implémentée (médiane/mode
  suffisaient ici) — à ajouter (`sklearn.impute.KNNImputer`) si un futur dataset réel présente
  des valeurs manquantes structurées (ex. capteur en panne).
- Isolation Forest et Z-score comme détecteurs *actifs* d'anomalies restent à implémenter
  explicitement ; seul l'IQR est actif dans le pipeline de production actuel.
