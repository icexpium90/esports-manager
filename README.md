# Gestion de structure esport

Outil web pour gérer une structure esport au quotidien : équipes (Valorant, CS2, Rainbow Six Siege,
Rocket League), roster et contrats, calendrier (matchs officiels, scrims, entraînements), résultats et
stats des joueurs, finances et sponsors. Comptes avec trois rôles : administrateur, staff et joueur.

## Lancer en local

```bash
python start.py
```

Le premier lancement crée `.venv` et installe les dépendances, puis ouvre http://localhost:1212.
Au premier accès, la page de bienvenue crée le compte administrateur.

Options : `--port 1313`, `--dev` (rechargement automatique), `--host 127.0.0.1 --no-browser` (serveur).
Le nom affiché se règle avec la variable `STRUCTURE_NAME` (par défaut « Ma structure »).

## Données

Tout est stocké dans `data/` (base SQLite `structure.db` et clé de session `secret.key`).
Sauvegarder ce dossier suffit : `cp -r data data-sauvegarde-$(date +%F)`.

## Rôles

| Rôle | Accès |
|---|---|
| Administrateur | Tout, y compris la gestion des comptes |
| Staff | Équipes, membres, contrats, calendrier, résultats, finances, sponsors |
| Joueur | Son équipe, le calendrier de son équipe, les résultats et son propre contrat |

Quand on ajoute un joueur avec son e-mail, son compte est créé automatiquement (case « Créer son compte d'accès ») et un mot de passe provisoire s'affiche. Pour un membre existant : bouton « Créer son compte » sur sa fiche.

## Inscription des joueurs

Les joueurs s'inscrivent eux-mêmes via le lien « S'inscrire » de la page de connexion (`/register`).
Leur compte reste bloqué jusqu'à validation par le staff dans **Inscriptions** (équipe, rôle et statut
choisis à la validation). Pour désactiver les inscriptions : variable `ALLOW_SIGNUP=0`.

## Contrats joueurs (PDF)

1. **Infos structure** (administrateur) : logo, texte sous le logo, dénomination, siège, représentants,
   signataires, lieu de signature, et un modèle d'articles par jeu (repris dans chaque nouveau contrat).
2. Sur la fiche d'un membre : **+ Contrat**, puis **Envoyer au joueur**.
3. Le joueur voit le contrat dans son espace, complète ses informations (adresse, date de naissance,
   représentant légal s'il est mineur…) et signe en ligne en recopiant son nom.
4. Tout le monde peut télécharger le PDF pré-rempli ; le staff peut aussi joindre une copie signée à la main.

La signature en ligne est une signature électronique simple (nom, date, heure et adresse IP dans le PDF).
Les modèles fournis sont indicatifs : à faire relire par un juriste.

## Mise en ligne

Voir [deploy/README.md](deploy/README.md).
