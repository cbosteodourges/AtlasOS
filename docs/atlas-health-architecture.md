# Atlas Santé — architecture fonctionnelle

## Finalité

Atlas Santé n’est ni un dossier médical ni un outil de diagnostic. Il transforme des observations de l’utilisateur, des données de charge et des données de récupération en :

1. une surveillance compréhensible ;
2. une orientation vers un professionnel lorsqu’un signal de vigilance est présent ;
3. une proposition explicable d’adaptation pour Atlas Coach ;
4. une mémoire chronologique de la tolérance à l’entraînement.

Aucune adaptation du programme validé ne doit être appliquée silencieusement.

## Navigation recommandée

- **Mon état** : récupération, sommeil, VFC, fréquence cardiaque de repos, charge récente, douleurs actives et évolution.
- **Signaler une douleur** : parcours anatomique guidé par région, côté et zone précise.
- **Problèmes en cours** : douleurs actives, évolution, activités tolérées et décisions prises.
- **Historique** : chronologie des déclarations, séances, réponses à 24/48/72 h et modifications validées.
- **Anatomie 3D avancée** : second niveau destiné à l’exploration précise, jamais porte d’entrée obligatoire.

L’ancienne rubrique autonome « Analyse Atlas » devient un panneau contextuel dans chaque problème et non une destination vide.

## Parcours de déclaration

1. Région : pied, cheville, jambe, genou, cuisse, hanche/aine, fesse, dos/bassin.
2. Zone précise et côté.
3. Intensité au repos et à la course, ancienneté, contexte et signes associés.
4. Niveau d’orientation :
   - surveillance ;
   - prudence et proposition de réduction de la charge irritante ;
   - vigilance, arrêt des impacts et avis professionnel.
5. Proposition Atlas Coach, toujours soumise à validation.

## Bibliothèque initiale du coureur

### Pied et cheville

- douleur plantaire et talonnière ;
- tendinopathie d’Achille ;
- douleur métatarsienne et suspicion de lésion de stress ;
- tendons extenseurs ;
- entorse latérale ou médiale ;
- tendons fibulaires et tibial postérieur.

### Jambe

- syndrome de stress tibial médial ;
- douleur osseuse tibiale focale ;
- surcharge du jambier antérieur ;
- surcharge du soléaire ou des gastrocnémiens.

### Genou

- douleur fémoro-patellaire ;
- tendon rotulien et pôle inférieur de la rotule ;
- tubérosité tibiale antérieure chez l’adolescent ;
- tendon quadricipital ;
- syndrome de la bandelette ilio-tibiale ;
- douleur des interlignes médial ou latéral avec recherche de blocage, gonflement ou perte d’amplitude.

### Cuisse, hanche, aine et fesse

- quadriceps et ischio-jambiers ;
- douleur liée aux adducteurs, à l’ilio-psoas, à la région inguinale ou pubienne ;
- douleur latérale de hanche et tendons fessiers ;
- grand et moyen fessiers ;
- douleur fessière profonde, en distinguant les signes neurologiques.

Cette bibliothèque décrit des **profils possibles à explorer**, jamais des diagnostics.

## Signaux de vigilance

Orientation rapide si l’utilisateur déclare notamment :

- impossibilité d’appui ou déformation après traumatisme ;
- gonflement brutal, articulation rouge et chaude ou fièvre ;
- blocage ou perte importante de mouvement ;
- faiblesse, engourdissement ou irradiation neurologique ;
- douleur nocturne inhabituelle ;
- douleur osseuse très localisée, surtout si elle augmente à l’appui.

## Connexion au moteur Atlas

Le rapport de douleur doit alimenter un objet longitudinal stable :

- localisation et côté ;
- intensité repos/effort ;
- ancienneté et évolution ;
- signaux associés ;
- charge aiguë et chronique ;
- dernière séance et surface ;
- récupération et Wellness ;
- activités tolérées ;
- décision de l’utilisateur et avis professionnel éventuel.

Le moteur produit une **proposition** :

- maintenir et surveiller ;
- réduire le volume ou l’intensité ;
- remplacer temporairement les impacts par vélo, elliptique ou repos ;
- suspendre les impacts et recommander une évaluation.

Atlas Coach affiche les observations utilisées, la raison, les séances concernées et demande une validation explicite.

## Sources de cadrage

- Kakouris N, Yener N, Fong DTP. *A systematic review of running-related musculoskeletal injuries in runners*. J Sport Health Sci. 2021. https://pubmed.ncbi.nlm.nih.gov/33862272/
- Fredette A et al. *Association between running-related injuries and running parameters*. J Athl Train. 2022. https://pubmed.ncbi.nlm.nih.gov/34478518/
- Willy RW et al. *Patellofemoral Pain Clinical Practice Guideline*. JOSPT. 2019. https://doi.org/10.2519/jospt.2019.0302
- Martin RL et al. *Achilles Pain, Stiffness, and Muscle Power Deficits: Midportion Achilles Tendinopathy Revision 2024*. https://pubmed.ncbi.nlm.nih.gov/39611662/
- Weir A et al. *Doha agreement meeting on terminology and definitions in groin pain in athletes*. https://scholars.duke.edu/publication/1294016

## Étapes suivantes nécessitant validation utilisateur

- wording exact des niveaux de vigilance ;
- règles de modification autorisées par type de douleur ;
- durée maximale d’une adaptation provisoire ;
- données pouvant être partagées avec un professionnel ;
- validation ergonomique sur smartphone et sur le modèle homme/femme.
