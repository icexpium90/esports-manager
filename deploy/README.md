# Mettre eSports Manager en ligne sur manager.luostatis.fr

Le jeu tourne en local sur le port **1212** (`127.0.0.1:1212`) et un reverse proxy
(nginx ou Caddy) le rend accessible sur `https://manager.luostatis.fr`.
Ainsi, aucun conflit avec ce qui utilise déjà les ports 8000 / 8080.

## 1. DNS

Chez ton registrar, dans la zone `luostatis.fr`, ajoute un enregistrement :

| Type | Nom     | Valeur              |
|------|---------|---------------------|
| A    | manager | IP publique du serveur |

Vérifie avec `ping manager.luostatis.fr` (la propagation peut prendre quelques minutes).

## 2. Installer le projet sur le serveur

```bash
sudo apt install -y python3 python3-venv git      # Python 3.12 minimum
sudo git clone https://github.com/icexpium90/esports-manager /opt/esports-manager
sudo chown -R www-data:www-data /opt/esports-manager
cd /opt/esports-manager
sudo -u www-data python3 start.py --host 127.0.0.1 --no-browser   # test, Ctrl+C pour arrêter
```

Le premier lancement crée `.venv`, installe les dépendances, crée la base et compile le CSS.

## 3. Lancement automatique (systemd)

```bash
sudo cp deploy/esports-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now esports-manager
sudo systemctl status esports-manager      # doit être "active (running)"
```

Logs : `journalctl -u esports-manager -f`

## 4. Reverse proxy

### Option A : nginx (si nginx est déjà installé)

```bash
sudo cp deploy/nginx-manager.luostatis.fr.conf /etc/nginx/sites-available/manager.luostatis.fr
sudo ln -s /etc/nginx/sites-available/manager.luostatis.fr /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# HTTPS gratuit avec Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d manager.luostatis.fr
```

### Option B : Caddy (HTTPS automatique)

Ajoute le contenu de `deploy/Caddyfile` dans `/etc/caddy/Caddyfile`, puis :

```bash
sudo systemctl reload caddy
```

## Mettre à jour

```bash
cd /opt/esports-manager
sudo -u www-data git pull
sudo systemctl restart esports-manager
```

## Changer de port

Remplace `1212` dans `esports-manager.service` **et** dans la config nginx/Caddy,
puis redémarre les deux services.
