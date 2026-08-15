from pathlib import Path

from fastapi.staticfiles import StaticFiles

from .main import app


_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

if not _FRONTEND_DIR.is_dir():
    raise RuntimeError("Production frontend assets are missing from the runtime image.")

# Production serves the compiled Glaze UI from the same origin as the API. Existing /api
# routes remain authoritative because this catch-all mount is registered after them.
app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
