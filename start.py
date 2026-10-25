"""
Lanceur de l'outil de gestion de structure (aucune dépendance à installer à la main).

    python start.py               -> http://localhost:1212
    python start.py --port 1313   -> autre port (ou variable APP_PORT)
    python start.py --dev         -> rechargement automatique du code
    python start.py --host 127.0.0.1 --no-browser   -> sur un serveur derrière Apache/nginx
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
DEFAULT_PORT = 1212


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def inside_venv() -> bool:
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def bootstrap():
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 ou plus récent est requis.")
    if not venv_python().exists():
        print("Création de l'environnement virtuel (.venv)...")
        venv.create(VENV_DIR, with_pip=True)
    req_hash = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    if not MARKER.exists() or MARKER.read_text().strip() != req_hash:
        print("Installation des dépendances...")
        subprocess.run([str(venv_python()), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
        subprocess.run([str(venv_python()), "-m", "pip", "install", "-q", "-r", str(REQUIREMENTS)], check=True)
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
    parser = argparse.ArgumentParser(description="Outil de gestion de structure esport")
    parser.add_argument("--port", type=int, default=int(os.environ.get("APP_PORT", DEFAULT_PORT)))
    parser.add_argument("--host", default=os.environ.get("APP_HOST", "0.0.0.0"))
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not port_is_free(args.port):
        sys.exit(f"Le port {args.port} est déjà utilisé. Essaie : python start.py --port {args.port + 1}")

    url = f"http://localhost:{args.port}"
    print(f"\nDémarrage sur {url}  (Ctrl+C pour arrêter)\n")
    if not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(2), webbrowser.open(url)), daemon=True).start()

    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", args.host, "--port", str(args.port),
           "--proxy-headers", "--forwarded-allow-ips", "*"]
    if args.dev:
        cmd.append("--reload")
    try:
        subprocess.run(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main() if inside_venv() else bootstrap()
