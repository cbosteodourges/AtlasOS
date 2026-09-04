# Mémoire Atlas — couleurs des frises de séance

## Invariant permanent

Dans une frise de séance planifiée, la couleur représente le rôle du bloc dans
la séance. Elle ne doit pas être déduite directement de sa seule zone
physiologique.

- **Bleu** : échauffement, endurance facile avant ou entre les efforts et
  récupération entre les fractions.
- **Jaune** : travail tempo, sous-SV2 ou SV2.
- **Orange** : travail VO2max ou VMA longue.
- **Rouge** : sprint, VMA courte ou travail anaérobie.
- **Vert** : retour au calme uniquement.

Ainsi, un bloc d'endurance Z2 situé avant les fractions reste bleu. Sa cible
physiologique demeure Z2 dans les données et les consignes ; seule sa fonction
visuelle est « préparation/endurance facile ». À l'inverse, un retour au calme
ciblé Z1 est vert.

## Implémentation de référence

La constante `ATLAS_TIMELINE_ROLE_COLORS` et la fonction
`plannedTimelineColor()` dans `app/js/atlas-training-calendar.js` constituent
la source de vérité. Toute nouvelle frise de séance doit les réutiliser plutôt
que recréer une correspondance locale entre zones et couleurs.

## Test de non-régression

`test_planned_timeline_uses_stable_semantic_colors` vérifie la présence de la
constante et l'application des couleurs sémantiques aux segments planifiés.
