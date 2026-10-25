# Mise en ligne sur manager.luostatis.fr (Apache)

```bash
# 1. Installer
sudo git clone -b gestion-structure https://github.com/icexpium90/esports-manager /opt/structure-manager
sudo chown -R www-data:www-data /opt/structure-manager

# 2. Service (adapter STRUCTURE_NAME dans le fichier si besoin)
sudo cp /opt/structure-manager/deploy/structure-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now structure-manager
sudo journalctl -u structure-manager -f      # attendre "Uvicorn running", puis Ctrl+C
```

Apache : la config existante de manager.luostatis.fr (port 1212, HTTPS via certbot) convient telle quelle.
Pour une nouvelle installation, voir `apache-manager.luostatis.fr.conf` puis `sudo certbot --apache -d manager.luostatis.fr`.

## Mettre à jour

```bash
cd /opt/structure-manager && sudo -u www-data git pull && sudo systemctl restart structure-manager
```

## Sauvegarder

```bash
sudo cp -r /opt/structure-manager/data /root/structure-backup-$(date +%F)
```
