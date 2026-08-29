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


## Contrat longitudinal des indicateurs

Atlas n'interprète jamais une mesure isolée uniquement à partir d'une norme
générale. Chaque indicateur doit être comparé à l'historique personnel, aux
journées associées aux meilleures réponses et au contexte disponible.

Tout moteur Atlas doit répondre explicitement à cinq questions :

1. **Référence personnelle** — quelle est la valeur habituelle de l'utilisateur ?
2. **Zone optimale** — quelles valeurs sont associées à ses meilleures réponses ?
3. **Évolution actuelle** — la mesure est-elle stable, favorable ou inhabituelle ?
4. **Conséquence probable** — quel effet plausible sur récupération, performance
   ou tolérance ?
5. **Conseil explicable** — quelle action proposer et avec quelle confiance ?

Le résultat suit le contrat commun
`PersonalIndicatorInterpreter` et expose au minimum : la mesure actuelle, la
référence personnelle, la zone optimale, l'évolution, la conséquence, le
conseil, le statut, la confiance, les données manquantes et le caractère complet
ou partiel de l'analyse.

Les statuts communs sont :

- **Optimal** : valeur historiquement favorable avec données suffisantes ;
- **À surveiller** : écart modéré, incertitude ou bilan partiel ;
- **Vigilance** : signal défavorable susceptible d'altérer la réponse.

Un score élevé issu de données partielles ne doit jamais être présenté comme
une certitude. Le ressenti et la réponse réelle à la séance servent à confirmer
ou corriger l'interprétation du matin.
