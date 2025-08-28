import html
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build paths
BUILD_DIR = os.path.join(os.path.dirname(__file__), "build")
INDEX_HTML = os.path.join(BUILD_DIR, "index.html")

# Serve static files from build directory
app.mount(
    "/assets", StaticFiles(directory=os.path.join(BUILD_DIR, "assets")), name="assets"
)


@app.get("/")
async def serve_index():
    return FileResponse(INDEX_HTML)


@app.get("/config")
async def get_config():
    backend_url = html.escape(os.getenv("BACKEND_API_URL", "http://localhost:8000"))
    auth_enabled = html.escape(os.getenv("AUTH_ENABLED", "false"))
    backend_url = backend_url + "/api"

    config = {
        "API_URL": backend_url,
        "ENABLE_AUTH": auth_enabled,
    }
    return config


@app.get("/{full_path:path}")
async def serve_app(full_path: str):
    # Remediation: normalize and check containment before serving
    file_path = os.path.normpath(os.path.join(BUILD_DIR, full_path))
    # Block traversal and dotfiles
    if not file_path.startswith(BUILD_DIR) or ".." in full_path or "/." in full_path or "\\." in full_path:
        return FileResponse(INDEX_HTML)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(INDEX_HTML)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)
