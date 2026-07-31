# Rapport d'Évaluation du Modèle

## Objectif

Fournir une évaluation complète et visuelle du modèle actif, au-delà des métriques
scalaires, pour permettre un diagnostic fin de son comportement (calibration, capacité de
ciblage, courbe d'apprentissage) — page `/evaluation`.

## Méthodes utilisées

Implémentées dans `ModelEvaluationService` (app/services/ml/model_evaluation_service.py),
en réutilisant le même split train/test que l'entraînement (même `random_state`) :

- Métriques : Accuracy, Precision, Recall, F1, ROC AUC, Balanced Accuracy, MCC, Log Loss,
  **Cohen Kappa** (ajouté spécifiquement pour ce module).
- Matrice de confusion (`sklearn.metrics.confusion_matrix`).
- Courbe ROC et courbe Precision-Recall.
- Courbe de calibration (`sklearn.calibration.calibration_curve`, 10 bins).
- **Lift Curve** et **Gain Curve** : implémentation maison (`_compute_lift_gain`) triant les
  prédictions par probabilité décroissante et calculant le gain cumulé et le lift par décile
  de population ciblée.
- **Learning Curve** (`sklearn.model_selection.learning_curve`, 5 tailles d'échantillon,
  validation croisée à 3 plis) sur un modèle de la même famille que le modèle actif, réentraîné
  avec des hyperparamètres par défaut (voir Limites).

## Résultats obtenus

Pour le modèle actif (CatBoost réglé) : ROC AUC ≈ 0.51, Cohen Kappa proche de 0 — cohérent
avec un modèle qui ne fait, au mieux, que très légèrement mieux que le hasard. La courbe de
calibration montre des probabilités prédites globalement peu informatives (proches du taux de
base de 24.6 % quel que soit le sous-groupe). La Gain Curve reste proche de la diagonale de
référence (aucun gain substantiel à cibler les scores les plus élevés), ce qui confirme
visuellement, en complément des métriques scalaires, l'absence de signal exploitable.

## Avantages

- Toutes les courbes demandées dans le cahier des charges sont implémentées et interactives
  (Plotly), y compris Lift/Gain qui ne sont pas fournies nativement par scikit-learn.
- La réutilisation du split d'entraînement garantit que l'évaluation correspond exactement au
  modèle réellement déployé, pas à une re-simulation approximative.

## Limites

- La Learning Curve réentraîne un modèle *par défaut* de la même famille plutôt que le modèle
  avec les hyperparamètres exacts retenus par Optuna, pour des raisons de temps de calcul —
  la courbe reste qualitativement représentative du comportement biais/variance de la famille
  de modèle, mais pas un remplacement exact du modèle en production.
- Le calcul complet de cette page prend environ 60 à 100 secondes (rechargement du dataset,
  ré-entraînement pour la Learning Curve) ; acceptable pour une page d'analyse consultée
  ponctuellement, pas conçue pour un rafraîchissement temps réel. Une mise en cache des
  résultats serait la prochaine optimisation naturelle.
