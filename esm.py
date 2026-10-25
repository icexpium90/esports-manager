# SPDX-FileCopyrightText: 2025 Pedrenrique G. Guimarães <admin@esportsmanager.net>
# SPDX-License-Identifier: GPL-3.0-or-later
# License-Filename: LICENSES/GPL-3.0-or-later
import webview
import uvicorn
import threading
from esm.app import create_api
from esm.config import Config
from frontend import create_frontend

config = Config()
config.load_config()
PORT = int(config.port)


def get_app():
    app = create_api()
    app = create_frontend(app)
    return app


def start_server():
    app = get_app()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    webview.create_window(
        "eSports Manager",
        f"http://localhost:{PORT}/",
        width=1200,
        height=800,
        resizable=True,
    )
    webview.start(icon="frontend/static/img/trophy.svg", gui="qt")
