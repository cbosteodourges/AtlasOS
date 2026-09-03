# Atlas — économie d'un prix de rupture

Date de calcul : 2 septembre 2026. Montants TTC en France, TVA supposée à 20 %. Ce modèle est une aide à la décision, pas une prévision comptable certifiée.

## Conclusion

Le prix de rupture recommandé est **24,99 € TTC par an**, vendu prioritairement sur le Web. C'est 79 % de moins que Campus à 119 €/an et 58 % de moins que Strava à 59,99 €/an, tout en laissant une contribution estimée de **15,40 € par abonné et par an** avant coûts fixes.

Un lancement à **19,99 €/an** est techniquement possible, mais il exige environ 6 900 abonnés pour financer un coût complet annuel de 78 k€. À 24,99 €, le même seuil descend à environ 5 100 abonnés. Un abonnement mensuel à 1,99 € est déconseillé : le coût fixe de chaque paiement détruit une part disproportionnée de la marge.

## Hypothèses variables par abonné et par an

| Poste | Hypothèse |
|---|---:|
| Hébergement, stockage, synchronisations | 2,40 € |
| Explications IA, usage parcimonieux | 0,60 € |
| Support, e-mails, incidents et remboursements | 1,80 € |
| **Total variable hors paiement** | **4,80 €** |

Le moteur de décision doit rester principalement déterministe. L'IA reformule et explique ; elle ne doit pas recalculer tout le programme à chaque affichage.

## Économie unitaire

Stripe facture actuellement 1,5 % + 0,25 € pour une carte standard de l'Espace économique européen. Apple annonce une commission réduite de 15 % pour les petites entreprises éligibles ; Google indique que plus de 99 % des développeurs soumis aux frais sont éligibles à 15 % ou moins.

| Prix annuel TTC | TVA | Paiement Web | Contribution Web | Contribution store à 15 % | Abonnés pour 18 k€ fixes | Abonnés pour 78 k€ coût complet |
|---:|---:|---:|---:|---:|---:|---:|
| 19,99 € | 3,33 € | 0,55 € | 11,31 € | 9,36 € | 1 592 | 6 897 |
| **24,99 €** | **4,16 €** | **0,62 €** | **15,40 €** | **12,90 €** | **1 169** | **5 065** |
| 29,99 € | 5,00 € | 0,70 € | 19,49 € | 16,44 € | 923 | 4 002 |

Le scénario « 18 k€ fixes » couvre un socle bootstrap (infrastructure, outils, juridique, comptabilité, sécurité et marge d'incident). Le scénario « 78 k€ » y ajoute 60 k€ de travail produit et technique annuel. Acquisition payante et rémunération d'une équipe de support élargie ne sont pas incluses.

## Stratégie tarifaire proposée

1. **Atlas Essentiel gratuit** : journal, saisies manuelles, import limité et aperçu du profil.
2. **Atlas Performance à 24,99 €/an** : plan vivant, analyse prescription/réalisation, profil physiologique longitudinal, récupération et décisions expliquées.
3. **Prix fondateur à 19,99 €/an**, verrouillé pour les premiers utilisateurs, seulement si l'acquisition est organique.
4. **Paiement annuel par défaut sur le Web** ; mensuel éventuel à 2,99 € minimum, pour éviter douze coûts fixes de transaction.
5. Ne pas subventionner une promesse impossible : aucune messagerie humaine 24/7 dans cette offre low cost.

## Taille de marché utilisable

Les sources publiques ne donnent pas un nombre certifié de coureurs français prêts à changer d'application. Il faut donc raisonner par entonnoir : environ 13,6 millions de pratiquants annuels sont cités en France ; une source 2025 évoque près de 4 millions d'utilisateurs de Strava en France. À titre de scénarios, convertir seulement 0,1 %, 0,25 % ou 0,5 % de 4 millions représenterait 4 000, 10 000 ou 20 000 abonnés. À 24,99 €/an, cela correspond à environ 62 k€, 154 k€ ou 308 k€ de contribution annuelle avant coûts fixes.

Ces chiffres ne sont pas une prévision de ventes. La prochaine validation doit mesurer trois taux réels : visite vers inscription, activation après trois séances et conversion en abonnement.

## Sources

- Stripe, tarification France : https://stripe.com/fr/pricing
- Apple, Small Business Program : https://developer.apple.com/app-store/small-business-program/
- Google Play, frais de service : https://support.google.com/googleplay/android-developer/answer/11131145
- Strava, rapport 2025 : https://press.strava.com/fr/articles/strava-releases-12th-annual-year-in-sport-trend-report-2025
- Marché français et ordre de grandeur Strava : https://www.marathons.com/grand-format/a-la-recherche-des-anti-strava-ces-coureurs-qui-fuient-les-donnees
