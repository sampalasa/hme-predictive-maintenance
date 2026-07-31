# Rapport d'Entraînement du Modèle (AutoML)

## Objectif

Comparer objectivement plusieurs familles de modèles de classification sur la tâche
`FailureWithin7Days`, optimiser automatiquement les hyperparamètres des meilleurs candidats,
et sélectionner puis versionner le meilleur modèle sans intervention manuelle.

## Méthodes utilisées

Pipeline implémenté dans `TrainingService`, `optuna_tuner.py`, `model_factory.py` et exécuté
par `app/ml/training/train_pipeline.py` (`python -m app.ml.training.train_pipeline`) :

1. Chargement + nettoyage + feature engineering (57 variables).
2. Split stratifié train/test (80/20, `random_state` fixe).
3. **SMOTE** sur le pli d'entraînement uniquement (classe minoritaire ~24.6 % → équilibrée).
4. Comparaison de 7 familles avec hyperparamètres par défaut : RandomForest, ExtraTrees,
   GradientBoosting, HistGradientBoosting, XGBoost, LightGBM, CatBoost.
5. **Optuna** (30 essais) sur les 3 meilleurs candidats du classement initial, avec un espace
   de recherche spécifique par famille (max_depth, learning_rate, n_estimators, subsample,
   gamma, min_child_weight, etc.).
6. Sélection du meilleur modèle (baseline + réglé) par score composite
   `0.5·F1 + 0.5·ROC AUC`, sauvegarde Joblib, enregistrement `ModelVersion` + `TrainingRun` en
   base (historique consultable dans Administration → Historique d'entraînement).

## Résultats obtenus

Diagnostic préalable (information mutuelle capteurs bruts / cible ≈ 0, voir `03_eda.md`) déjà
posé avant l'entraînement. Résultat du dernier entraînement complet :

| Modèle | Accuracy | F1 | ROC AUC | Composite |
|---|---|---|---|---|
| XGBoost (baseline) | 0.726 | 0.090 | 0.493 | 0.291 |
| CatBoost (tuned) — **retenu** | 0.739 | 0.078 | 0.511 | 0.294 |
| ExtraTrees (tuned) | 0.747 | 0.027 | 0.485 | 0.256 |

Le modèle actif (CatBoost réglé) est marginalement meilleur que le hasard (ROC AUC = 0.51),
ce qui est attendu et documenté automatiquement dans `TrainingRun.notes` par
`_diagnose_signal_quality()` (calcul d'information mutuelle intégré au script
d'entraînement, qui avertit explicitement si le signal est proche de zéro).

## Avantages

- AutoML + Optuna entièrement automatisés, aucune intervention manuelle nécessaire pour
  ajouter un futur modèle réel : il suffit de relancer le script sur un dataset avec signal.
- Le diagnostic de qualité du signal est intégré *dans* le pipeline (pas seulement en EDA),
  donc impossible à manquer même en exécution automatisée/planifiée (voir `08_mlops.md`).
- Toutes les métriques demandées sont calculées : Accuracy, Precision, Recall, F1, ROC AUC,
  Balanced Accuracy, MCC, Log Loss (+ Cohen Kappa dans le module d'évaluation avancée).

## Limites

- Le modèle actif n'a pas de valeur prédictive opérationnelle réelle sur ce dataset précis
  (limite du **jeu de données synthétique**, pas de l'architecture ni du pipeline —
  confirmé indépendamment par EDA, entraînement et information mutuelle).
- SMOTE est appliqué globalement sur le pli d'entraînement puis l'optimisation Optuna
  effectue sa propre validation croisée sur ces données déjà suréchantillonnées, ce qui
  peut légèrement optimiser le score de validation croisée par rapport à une image plus
  stricte (SMOTE recalculé à l'intérieur de chaque pli) — le score sur le jeu de test final
  (non suréchantillonné) reste la mesure de référence utilisée pour la sélection.
