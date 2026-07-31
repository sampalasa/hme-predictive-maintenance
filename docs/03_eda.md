# Rapport d'Analyse Exploratoire des Données (EDA)

## Objectif

Comprendre la structure, la distribution et les relations statistiques du dataset
`HME_Downtime` avant toute modélisation, et vérifier explicitement l'hypothèse implicite
du projet — que les capteurs (température, pression, vibration, heures de fonctionnement)
permettent de prédire une panne dans les 7 jours.

## Méthodes utilisées

Implémentées dans `EdaService` (app/services/eda_service.py), exposées sur la page `/eda` :

- Statistiques descriptives (moyenne, écart-type, min/max, quartiles, asymétrie) par variable.
- Histogrammes et boxplots (détection visuelle d'outliers) pour les 4 variables numériques.
- Heatmap de corrélation (Pearson) entre variables numériques et la cible.
- Pair plot interactif (Plotly `scatter_matrix`), coloré par la cible, sur un échantillon de
  800 lectures.
- Distribution de la cible, analyse par type d'équipement, par mode de panne, et évolution
  temporelle mensuelle des pannes détectées.
- Export PDF de l'ensemble (bouton "Exporter en PDF", rendu via Plotly→PNG avec kaleido puis
  assemblage ReportLab).

## Résultats obtenus

- 10 000 lignes, 9 colonnes, 1 doublon, 0 valeur manquante, taux de panne cible = 24.6 %.
- **Constat statistique central** : la matrice de corrélation et l'information mutuelle
  (calculée dans le pipeline d'entraînement, voir `05_model_training.md`) montrent une
  corrélation quasi nulle (|r| < 0.02) entre chacun des 4 capteurs bruts et
  `FailureWithin7Days`, et un taux de panne quasi identique (23.4 % à 26.5 %) dans tous les
  sous-groupes (type d'équipement, mode de panne). Le pair plot confirme visuellement
  l'absence de séparation entre les classes sur les variables brutes.
- Ce constat, obtenu *avant* toute modélisation grâce à l'EDA, explique et anticipe la
  performance proche du hasard (ROC AUC ≈ 0.51) observée lors de l'entraînement — l'EDA a
  donc joué son rôle méthodologique : éviter de chercher un bug dans le pipeline ML alors
  que la limite vient du jeu de données.

## Avantages

- Diagnostiquer un manque de signal *avant* l'entraînement plutôt qu'après, économisant du
  temps de calcul et évitant une fausse piste de débogage.
- Visualisations interactives (Plotly) exploitables directement dans une soutenance.

## Limites

- Le pair plot est calculé sur un échantillon (800 lignes) pour rester interactif dans le
  navigateur — pas une vue exhaustive des 10 000 lignes.
- L'EDA recharge le fichier Excel source à chaque appel plutôt que de mettre en cache le
  résultat ; acceptable pour un dataset de 10k lignes (~1s de chargement) mais à revoir pour
  un dataset nettement plus volumineux.
