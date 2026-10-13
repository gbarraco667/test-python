import logging
import os
import platform
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import APP_NAME, PACKAGE, VERSION
from .db import fetch_all, fetch_one, migrate, pool, wait_for_database

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("app")

STARTED_AT = datetime.now(timezone.utc)
STARTED_MONO = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_database()
    await migrate()
    log.info("🚀 %s v%s listo", APP_NAME, VERSION)
    yield
    log.info("cerrando...")
    await pool.close()
    log.info("cerrado correctamente")


app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)


def memory_mb() -> int | None:
    # RSS actual (Linux). En otros sistemas devuelve None.
    try:
        rss_pages = int(Path("/proc/self/statm").read_text().split()[1])
        return round(rss_pages * os.sysconf("SC_PAGE_SIZE") / 1024 / 1024)
    except (OSError, ValueError, AttributeError):
        return None


# Liveness: el proceso está vivo
@app.get("/health")
async def health():
    return {"status": "ok"}


# Readiness: el proceso puede atender (la base responde)
@app.get("/ready")
async def ready():
    try:
        await fetch_one("SELECT 1")
        return {"status": "ready", "database": "up"}
    except Exception as err:
        return JSONResponse(
            {"status": "not_ready", "database": "down", "error": str(err)}, status_code=503
        )


@app.get("/api/info")
async def info():
    data = {
        "app": APP_NAME,
        "package": PACKAGE,
        "version": VERSION,
        "environment": os.getenv("APP_ENV", "development"),
        "commit": os.getenv("GIT_COMMIT") or None,
        "deployedAt": os.getenv("DEPLOYED_AT") or None,
        "python": platform.python_version(),
        "hostname": socket.gethostname(),
        "platform": f"{platform.system().lower()} {platform.machine()}",
        "startedAt": STARTED_AT.isoformat(),
        "uptimeSeconds": round(time.monotonic() - STARTED_MONO),
        "memoryMb": memory_mb(),
        "database": {"status": "down"},
    }

    try:
        started = time.perf_counter()
        row = await fetch_one(
            "SELECT version() AS version, current_database() AS name, NOW() AS now"
        )
        data["database"] = {
            "status": "up",
            "latencyMs": round((time.perf_counter() - started) * 1000),
            "name": row["name"],
            "version": row["version"].split(" on ")[0],
            "serverTime": row["now"].isoformat(),
        }
    except Exception as err:
        data["database"]["error"] = str(err)

    return data


@app.post("/api/visits")
async def visits():
    row = await fetch_one("UPDATE visits SET total = total + 1 WHERE id = 1 RETURNING total")
    return {"total": int(row["total"])}


@app.get("/api/messages")
async def list_messages():
    return await fetch_all(
        "SELECT id, author, content, created_at FROM messages ORDER BY created_at DESC LIMIT 50"
    )


class MessageIn(BaseModel):
    author: str = ""
    content: str = ""


@app.post("/api/messages", status_code=201)
async def create_message(body: MessageIn):
    author, content = body.author.strip(), body.content.strip()

    if not author or not content:
        return JSONResponse({"error": "author y content son obligatorios"}, status_code=400)
    if len(author) > 60 or len(content) > 280:
        return JSONResponse({"error": "author máx. 60 caracteres, content máx. 280"}, status_code=400)

    return await fetch_one(
        "INSERT INTO messages (author, content) VALUES (%s, %s) "
        "RETURNING id, author, content, created_at",
        (author, content),
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, err: Exception):
    log.exception("error en %s %s", request.method, request.url.path)
    return JSONResponse({"error": "Error interno", "detail": str(err)}, status_code=500)


# Va al final: las rutas de arriba tienen prioridad sobre los estáticos
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
