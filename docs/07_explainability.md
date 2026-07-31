# Rapport d'Explicabilité (Explainable AI)

## Objectif

Rendre chaque prédiction individuelle interprétable pour un ingénieur de maintenance :
répondre concrètement à "pourquoi cette machine est-elle jugée à risque ?", avec un
niveau de confiance et une recommandation d'action — pages `/explainability` et
`/explainability/equipment/<code>`.

## Méthodes utilisées

Implémentées dans `ExplainabilityService` (app/services/ml/explainability_service.py), en
s'appuyant sur **SHAP** (`shap.TreeExplainer`, compatible RandomForest, ExtraTrees,
GradientBoosting, HistGradientBoosting, XGBoost, LightGBM et CatBoost) :

- **Explication globale** : valeur SHAP moyenne absolue par variable sur un échantillon de la
  flotte (jusqu'à 500 lectures), classement des 20 variables les plus influentes,
  visualisé en bar chart sur `/explainability`.
- **Explication locale** : pour un équipement donné, calcul des valeurs SHAP de sa dernière
  lecture (feature engineering exécuté sur tout son historique pour garantir la cohérence
  train/serve), extraction des 10 variables à plus fort impact absolu, séparées en facteurs
  qui *augmentent* et qui *réduisent* le risque.
- **Narration automatique** (`_build_narrative`) : génère une explication en langage naturel
  citant la probabilité, les 3 principaux facteurs de hausse/baisse du risque, un niveau de
  confiance qualitatif, et une recommandation d'action (inspection préventive si risque ≥ 60 %,
  surveillance de routine sinon).
- LIME n'a pas été implémenté en plus de SHAP : les deux méthodes sont redondantes sur des
  modèles d'arbres (SHAP y est exact et plus rapide via `TreeExplainer`, alors que LIME est
  surtout utile pour des modèles boîte noire non supportés par un explainer dédié) ; SHAP a
  donc été retenu comme unique méthode de production.

## Résultats obtenus

Le graphique d'importance globale et les explications locales sont fonctionnels et testés
(`GET /explainability/equipment/EQ-057` → 200, valeurs SHAP calculées et affichées). Conforme
au constat des sections précédentes, les valeurs SHAP absolues restent faibles en amplitude —
la hiérarchie relative des variables reste néanmoins informative et démontre correctement le
mécanisme d'explicabilité, prêt à produire des explications fortes dès qu'un modèle entraîné
sur des données à signal réel sera déployé.

## Avantages

- Explication *actionnable* (langage naturel + recommandation), pas seulement un tableau de
  chiffres SHAP bruts.
- Réutilise le même `FeatureEngineeringService` que l'entraînement et la prédiction : les
  valeurs expliquées sont exactement celles vues par le modèle, sans risque de divergence.

## Limites

- Pas de Force Plot ni Dependence Plot HTML natifs de la librairie `shap` (qui nécessitent du
  JavaScript embarqué complexe) — remplacés par des bar charts Chart.js plus simples à intégrer
  dans le thème de l'application et suffisants pour l'usage métier visé.
- L'explication globale est calculée sur un échantillon (max 500 lectures) pour rester rapide ;
  un calcul exhaustif sur 10 000 lignes serait plus lent sans changer la conclusion qualitative.
