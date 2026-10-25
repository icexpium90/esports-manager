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

Pour un compte joueur, lier le compte à sa fiche membre (page Comptes).

## Mise en ligne

Voir [deploy/README.md](deploy/README.md).
