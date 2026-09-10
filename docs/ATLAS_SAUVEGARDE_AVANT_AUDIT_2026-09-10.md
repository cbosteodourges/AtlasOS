# AtlasOS — sauvegarde avant audit et retour arrière

Date : 10 septembre 2026. Cette procédure complète la sauvegarde du code ; **elle n’a pas été exécutée sur le PC de Christophe**.

## Ce qui est déjà vérifié

- Dépôt : `cbosteodourges/AtlasOS`, branche `health-connect-auto-sync`.
- Référence GitHub : `backup/atlas-pre-audit-2026-09-10-305088f`.
- Commit exact : `305088f69b6c67807f052a6361fb3e5438d82ffe`.
- Arbre exact : `d624048772b286e15ac4f618322e7f572c567bd8`.
- Référence distante créée puis relue ; clone propre, `git fsck --full` réussi.
- Bundle Git complet créé et vérifié ici. Restauration dans une copie isolée : même commit, même arbre, aucun changement suivi.
- L’ancienne copie de travail présente dans cet environnement a été laissée intacte : commit `9c237d8`, arbre identique, aucun fichier suivi modifié ni fichier non suivi ; 199 fichiers ignorés, tous des caches Python `.pyc`. Elle ne contient pas les fichiers privés du PC.

La branche distante conserve durablement le code suivi. Le bundle est une copie de contrôle locale, **pas une sauvegarde privée du PC**. La référence Git n’est pas immuable : ne pas la déplacer ou la supprimer.

## Ce qui doit encore être sauvegardé sur Windows

Le dossier complet du projet, incluant `.git`, modifications non commitées, fichiers ignorés et non suivis, `.env`, configuration Android locale et `atlas-data`. Ajouter les archives FIT/Wellness et configurations situées ailleurs avec `-ExtraPath`.

Les déclarations Santé, préférences et certaines décisions de calendrier résident aussi dans `localStorage`. Chaque origine est différente : `127.0.0.1:8011`, `localhost:8011` et l’adresse Wi-Fi du PC ne partagent pas leur stockage. Chrome, Edge et la WebView Android sont également distincts.

La sauvegarde ci-dessous ne couvre pas les données natives Android, les jetons de l’application Atlas Connect, la base Santé Connect, les appareils non exportés ni les répertoires externes non indiqués. Aucune suppression de données d’application, réinstallation avec effacement, migration ou changement d’origine ne doit être entrepris avant une procédure spécifique pour ces éléments.

## 1. Exporter le navigateur utilisé pour Atlas

Ouvrir l’Atlas habituel dans son navigateur habituel. Ouvrir les outils de développement (F12), onglet Console. Exécuter ce code **sur la page Atlas**, jamais sur un autre site :

```javascript
(() => {
  const storage = Object.fromEntries(Array.from({length: localStorage.length}, (_, i) => {
    const key = localStorage.key(i);
    return [key, localStorage.getItem(key)];
  }));
  const session_storage = Object.fromEntries(Array.from({length: sessionStorage.length}, (_, i) => {
    const key = sessionStorage.key(i);
    return [key, sessionStorage.getItem(key)];
  }));
  const exportData = {
    schema: 'atlas-local-backup-v1', origin: location.origin,
    created_at: new Date().toISOString(), storage, session_storage
  };
  const blob = new Blob([JSON.stringify(exportData, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'atlas-navigateur-' + location.host.replace(/[^a-z0-9.-]/gi, '-') + '-' + Date.now() + '.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
})();
```

Ce code lit le stockage et télécharge un JSON. Il ne modifie ni n’efface les données Atlas. Conserver le fichier privé, même s’il contient peu de clés. Répéter pour les autres origines et navigateurs réellement utilisés. Si la Console bloque le collage, ne pas désactiver ses protections : prévoir une autre méthode d’export avant de modifier ce navigateur.

Aucun usage d’IndexedDB ou de sessionStorage n’a été retrouvé dans le code applicatif parcouru ; sessionStorage est néanmoins exporté par précaution. Les caches du service worker ne sont pas archivés par cet export. Il ne s’agit pas d’une copie intégrale du profil Chrome/Edge.

**Android** : l’export PC ne sauvegarde pas la WebView. Ne pas effacer son stockage. Un export du stockage WebView devra être prévu et vérifié avant toute modification susceptible de le migrer. Une copie ADB n’est pas annoncée comme disponible sans vérifier les capacités de la version installée.

## 2. Mettre les écritures en pause

Attendre que les importations et synchronisations soient terminées. Fermer les pages Atlas après export. Couper temporairement la connexion réseau du téléphone pour éviter une reprise de synchronisation. Fermer le serveur et les deux watchers Atlas.

Le script refuse de démarrer s’il détecte les processus Python Atlas habituels et indique leurs PID, sans les arrêter. Dans ce cas, vérifier ces PID dans le Gestionnaire des tâches et fermer uniquement les processus Atlas concernés lorsqu’ils sont inactifs. Ne pas arrêter tous les processus Python indistinctement. Si une importation écrit encore, attendre sa fin.

Ne pas modifier le dossier pendant la copie. Mettre en pause les autres programmes susceptibles d’y écrire. Les fichiers OneDrive doivent être lisibles localement ; leur lecture peut déclencher leur téléchargement. Une erreur de lecture invalide la sauvegarde.

## 3. Exécuter le script téléchargé

Le script peut être téléchargé directement depuis la conversation ; aucun `git pull` préalable n’est nécessaire. Exemple à adapter aux noms exacts des fichiers téléchargés :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\backup_atlas_before_audit.ps1" `
  -ProjectPath "$env:USERPROFILE\OneDrive\Documents\GitHub\AtlasOS" `
  -BrowserExport "$env:USERPROFILE\Downloads\atlas-navigateur-REMPLACER.json"
```

Pour plusieurs exports, appeler le script depuis PowerShell :

```powershell
& "$env:USERPROFILE\Downloads\backup_atlas_before_audit.ps1" `
  -BrowserExport @('C:\chemin\export-chrome.json', 'C:\chemin\export-edge.json') `
  -ExtraPath @('D:\ArchivesGarmin')
```

`-ExtraPath` est facultatif. Les chemins d’exemple doivent être remplacés par les vrais chemins. Ne pas inclure la destination de sauvegarde parmi les sources.

Le script crée un nouveau dossier daté sous `%LOCALAPPDATA%\AtlasOS-Backups`, en dehors du dépôt et de son dossier OneDrive. Il restreint ses droits à l’utilisateur courant et SYSTEM. Il copie les fichiers sans `/MIR`, sans suppression et sans `git reset`. Les empreintes SHA-256 de la source avant/après et de la copie doivent correspondre. Il vérifie le commit et les objets Git de la copie.

La validation n’est acquise que si le message final est vert et si `SAUVEGARDE-VERIFIEE.txt` est présent. Un dossier partiellement copié n’est pas une sauvegarde validée. Le script ne garantit pas une transaction instantanée entre des fichiers modifiés par un programme inconnu : d’où la pause des écritures.

**Validation locale encore nécessaire** : PowerShell et Windows ne sont pas disponibles dans l’environnement d’audit. Le script a été relu, mais son exécution Windows, Robocopy, les ACL et le parcours OneDrive restent à vérifier sur le PC. Aucun succès Windows n’est revendiqué.

Communiquer seulement : « sauvegarde OK », le nombre de navigateurs/origines exportés et les éléments manquants. Ne pas envoyer les fichiers privés ou le manifeste détaillé.

## Annuler un futur lot sans perdre les nouvelles séances

Les futurs commits doivent séparer interface, calcul, synchronisation et données. Un commit d’interface ne doit contenir que des fichiers de présentation ; aucune migration de stockage ou modification du moteur.

Pour retirer ce lot : vérifier d’abord la branche, les modifications locales et le contenu du commit. Préparer `git revert --no-commit IDENTIFIANT_DU_LOT` dans une copie isolée à jour ; examiner le diff, résoudre les conflits uniquement dans les fichiers du lot, tester, puis créer un nouveau commit de réversion. Ne pas rétablir tout le dossier `atlas-data` depuis l’ancienne sauvegarde : cela supprimerait les activités ajoutées depuis.

Ne jamais employer `git reset --hard`, `git clean`, un force-push ou une restauration globale de `localStorage` pour simplement annuler une interface. Un conflit impose une résolution ciblée, pas l’écrasement des nouvelles données.

Le prototype actuel n’est chargé par aucune page de l’application. Le fermer suffit à cesser de l’utiliser. Ses exemples vivent en mémoire et n’ont aucun effet sur Atlas. Le supprimer ensuite ne nécessite aucune restauration de données.

Pour tester une restauration privée complète, travailler exclusivement dans un nouveau dossier hors de l’installation active, avec téléphone déconnecté. Vérifier les empreintes ; ne lancer aucun watcher. Le lancement applicatif et la restauration navigateur doivent faire l’objet d’un essai distinct, sur profil navigateur isolé et copie de données, avec une adresse locale choisie explicitement. Cet essai Windows n’a pas encore eu lieu.
