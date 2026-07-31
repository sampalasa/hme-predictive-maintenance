# Rapport d'Ingénierie des Caractéristiques (Feature Engineering)

## Objectif

Transformer les 4 signaux bruts (heures de fonctionnement, température moteur, pression
hydraulique, vibration) et les 2 identifiants catégoriels (type d'équipement, mode de panne)
en un espace de variables riche, exploitable par les modèles d'ensemble, en encodant la
dynamique temporelle par équipement, des scores de risque métier, et des interactions.

## Méthodes utilisées

Implémentées dans `FeatureEngineeringService` (app/services/data/feature_engineering_service.py),
organisées en 5 familles (57 variables au total sur le dataset actuel, ≥ 30 exigées) :

1. **Temporelles / par équipement** : moyennes et écarts-type glissants (fenêtres 3 et 7),
   valeurs décalées (lag-1), delta, pente de tendance approximative, jours depuis la dernière
   lecture — calculées par `groupby("EquipmentID")` trié chronologiquement.
2. **Scores de risque** : TemperatureRiskScore, PressureRiskScore, VibrationRiskScore (seuils
   métier définis dans `app/utils/constants.py`), HydraulicStressScore, EngineHealthScore,
   HealthScore composite, FailureRiskIndex.
3. **Usage / cycle de vie** : EquipmentAgeScore (percentile des heures par type), UsageScore,
   OperatingEfficiency, OperatingLoad, PredictedRemainingLife (heuristique basée sur la
   médiane des heures de fonctionnement au moment des pannes historiques, par type),
   CriticalityScore, MaintenancePriority et EquipmentConditionScore (encodages ordinaux).
4. **Interactions** : produits et ratios entre capteurs (EngineTemp×Vibration,
   HydraulicPressure×OperatingHours, Vibration/OperatingHours), z-scores par type d'équipement.
5. **Encodages** : one-hot du type d'équipement, fréquence du mode de panne, encodage cyclique
   (sinus/cosinus) du mois, jour de semaine et heure.

## Résultats obtenus

57 variables dérivées produites automatiquement, listées dans
`app/ml/artifacts/*_features.json` à chaque entraînement pour garantir la cohérence
train/serve. Le module de sélection de variables (`/feature-selection`) confirme que même
les variables les plus haut classées (Mutual Information, RFE, Permutation Importance, SHAP)
n'atteignent que des scores très faibles en valeur absolue — cohérent avec le constat de
l'EDA : aucune transformation ne peut créer un signal qui n'existe pas dans les données brutes.

## Avantages

- Génération entièrement automatique et déterministe (même `random_state`), donc reproductible.
- Séparation stricte en méthodes privées par famille — chaque variable est traçable à sa
  définition dans le code, ce qui documente le "pourquoi" de chaque colonne.
- Le service est réutilisé identiquement par l'entraînement, la prédiction individuelle, la
  prédiction de flotte et l'explicabilité SHAP : aucune divergence possible entre les features
  vues à l'entraînement et celles vues en production.

## Limites

- `PredictedRemainingLife` utilise une agrégation calculée sur l'ensemble du dataset (y compris
  au moment du split train/test), ce qui introduit une fuite d'information légère et
  optimiste au niveau population (pas au niveau ligne) — acceptable en démonstration mais à
  recalculer strictement sur le pli d'entraînement dans un pipeline de production rigoureux.
- La pente de tendance (`_TrendSlope`) est une approximation par différence simple plutôt
  qu'une régression linéaire complète, choisie pour la performance sur 10 000 lignes.
