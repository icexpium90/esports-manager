# SPDX-FileCopyrightText: 2025 Pedrenrique G. Guimarães <admin@esportsmanager.net>
# SPDX-License-Identifier: GPL-3.0-or-later
# License-Filename: LICENSES/GPL-3.0-or-later
"""
Lanceur tout-en-un d'eSports Manager (sans uv).

    python start.py              -> installe si besoin et lance le jeu sur http://localhost:1212
    python start.py --port 1313  -> autre port
    python start.py --dev        -> mode développement (rechargement automatique)
    python start.py --no-browser -> ne pas ouvrir le navigateur

Le port peut aussi être fixé avec la variable d'environnement ESM_PORT.
"""

import argparse
import hashlib
import os
import socket
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
MARKER = VENV_DIR / ".requirements.sha256"
DB_FILE = ROOT / "esm" / "app.db"
DEFAULT_PORT = 1212


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def inside_venv() -> bool:
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def run(cmd, **kwargs):
    print(">", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], cwd=ROOT, **kwargs)


def bootstrap():
    """Crée le venv, installe les dépendances, puis relance ce script dans le venv."""
    if sys.version_info < (3, 12):
        sys.exit("Python 3.12 ou plus récent est requis : https://www.python.org/downloads/")

    if not venv_python().exists():
        print("Création de l'environnement virtuel (.venv)...")
        venv.create(VENV_DIR, with_pip=True)

    req_hash = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    if not MARKER.exists() or MARKER.read_text().strip() != req_hash:
        print("Installation des dépendances...")
        run([venv_python(), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        run([venv_python(), "-m", "pip", "install", "-r", REQUIREMENTS], check=True)
        MARKER.write_text(req_hash)

    result = subprocess.run([str(venv_python()), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT)
    sys.exit(result.returncode)


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False


def main():
    parser = argparse.ArgumentParser(description="Lance eSports Manager")
    parser.add_argument("--port", type=int, default=int(os.environ.get("ESM_PORT", DEFAULT_PORT)))
    parser.add_argument("--host", default=os.environ.get("ESM_HOST", "0.0.0.0"),
                        help="127.0.0.1 derrière un reverse proxy (nginx, Caddy...)")
    parser.add_argument("--dev", action="store_true", help="rechargement automatique du code")
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    args = parser.parse_args()

    os.environ["ESM_PORT"] = str(args.port)

    if not port_is_free(args.port):
        sys.exit(
            f"Le port {args.port} est déjà utilisé. Choisis-en un autre, par exemple :\n"
            f"    python start.py --port {args.port + 1}"
        )

    # 1. Base de données (seulement au premier lancement)
    if not DB_FILE.exists():
        print("Initialisation de la base de données...")
        run([sys.executable, "scripts/init_db.py"], check=True)

    # 2. CSS Tailwind (téléchargé au premier lancement ; on continue même en cas d'échec)
    try:
        run(
            [sys.executable, "-m", "pytailwindcss", "-i", "frontend/static/css/input.css",
             "-o", "frontend/static/css/tailwind.css", "--minify"],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Attention : la compilation du CSS a échoué, le style peut être incomplet.")

    # 3. Serveur
    url = f"http://localhost:{args.port}"
    print(f"\neSports Manager démarre sur {url}  (Ctrl+C pour arrêter)\n")

    if not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(2), webbrowser.open(url)), daemon=True).start()

    cmd = [sys.executable, "-m", "uvicorn", "dev:app", "--host", args.host, "--port", str(args.port),
           "--proxy-headers", "--forwarded-allow-ips", "*"]
    if args.dev:
        cmd.append("--reload")
    try:
        run(cmd)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if inside_venv():
        main()
    else:
        bootstrap()
