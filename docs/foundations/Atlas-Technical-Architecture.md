# Atlas Technical Architecture

**Version :** 0.3.0

## Moteurs

- `src/twin/atlas-twin.js` : Digital Twin et chronologie ;
- `src/human/human-context.js` : contexte professionnel, quotidien et récupération ;
- `src/clinical/clinical-engine.js` : facteurs, symptômes, hypothèses et orientation ;
- `src/training/adaptive-training.js` : progressivité de charge et capacité d’adaptation.

Les moteurs sont testés séparément avant leur intégration dans `app.js`.
