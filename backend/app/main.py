"""SiteBrain AI — BUU Operations Copilot API."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, knowledge, llm, seed
from .routers import admin, kb, misc, ops, plant, sessions, setup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed.seed()
    knowledge.train()
    logging.getLogger("sitebrain").info("Diagnostic engine: %s", llm.status()["engine"])
    yield
    db.close()


app = FastAPI(title="SiteBrain AI", version="1.0.0", lifespan=lifespan,
              description="Unified conversational operations & technical escalation copilot for Biogas Upgradation Units")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (misc.router, admin.router, plant.router, setup.router, sessions.router, ops.router, kb.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.status()}


# Serve the built frontend when present (single-process deployment: `npm run build` then run uvicorn).
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        f = DIST / full_path
        return FileResponse(f if full_path and f.is_file() else DIST / "index.html")
