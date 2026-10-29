"""Point d'entrée de l'application de gestion de structure esport."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .db import init_db
from .routes import auth, calendar, contracts, dashboard, finances, members, signup, teams, users
from .security import Forbidden, LoginRequired, secret_key
from .web import render, redirect

app = FastAPI(title="Gestion de structure esport", docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key(),
    session_cookie="structure_session",
    max_age=60 * 60 * 24 * 14,
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

for module in (auth, signup, dashboard, teams, members, contracts, calendar, finances, users):
    app.include_router(module.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.exception_handler(LoginRequired)
async def login_required(request: Request, exc: LoginRequired):
    return redirect("/login")


@app.exception_handler(Forbidden)
async def forbidden(request: Request, exc: Forbidden):
    response = render(request, "error.html", code=403, message="Tu n'as pas accès à cette page.")
    response.status_code = 403
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    message = "Page introuvable." if exc.status_code == 404 else str(exc.detail)
    response = render(request, "error.html", code=exc.status_code, message=message)
    response.status_code = exc.status_code
    return response
