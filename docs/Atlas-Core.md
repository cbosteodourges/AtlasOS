# Atlas OS — Core

**Cycle :** Genesis  
**Version :** 0.1.0  
**Statut :** Fondation

> Le Digital Twin n'est pas une représentation du corps.  
> C'est la représentation de l'interaction permanente entre le corps, son histoire, son environnement et ses objectifs.

## Convention des parties

- 🟦 PARTIE A — Configuration et structures
- 🟩 PARTIE B — Initialisation
- 🟨 PARTIE C — Données et événements
- 🟧 PARTIE D — Logique métier
- 🟪 PARTIE E — Intelligence et analyses
- 🟥 PARTIE F — Validation et sécurité
- ⬜ PARTIE G — API publique et utilitaires

Chaque partie possède un identifiant stable, par exemple `A01`, `B01` ou `G02`.

## Règles de développement

1. Un fichier complet est préféré à un fragment isolé.
2. Une modification locale doit remplacer une PARTIE entière.
3. Toute nouvelle fonctionnalité doit être documentée.
4. Les données de santé doivent rester nuancées et explicables.
5. Atlas ne doit jamais présenter une hypothèse comme une certitude.
6. La branche `main` reste stable ; les essais sont réalisés dans une branche dédiée.

## Premier module

Le premier module du cycle Genesis est :

```text
src/twin/atlas-twin.js
```

Sa première version crée une structure de Digital Twin vide, valide et exportable.
