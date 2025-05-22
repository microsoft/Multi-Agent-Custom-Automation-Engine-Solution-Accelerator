import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles

# Resolve wwwroot path relative to this script
WWWROOT_PATH = os.path.join(os.path.dirname(__file__), "wwwroot")

# Debugging information
print(f"Current Working Directory: {os.getcwd()}")
print(f"Absolute path to wwwroot: {WWWROOT_PATH}")
if not os.path.exists(WWWROOT_PATH):
    raise FileNotFoundError(f"wwwroot directory not found at path: {WWWROOT_PATH}")
print(f"Files in wwwroot: {os.listdir(WWWROOT_PATH)}")

app = FastAPI()

import html


@app.get("/config.js", response_class=PlainTextResponse)
def get_config():
    backend_url = html.escape(os.getenv("BACKEND_API_URL", "http://localhost:8000"))
    auth_enabled = html.escape(os.getenv("AUTH_ENABLED", "True"))
    backend_url = backend_url + "/api"
    return f"""
        const BACKEND_API_URL = "{backend_url}";
        const AUTH_ENABLED = "{auth_enabled}";
        """


# Redirect root to app.html
@app.get("/")
async def index_redirect():
    return RedirectResponse(url="/app.html?v=home")


# Mount static files
app.mount("/", StaticFiles(directory=WWWROOT_PATH, html=True), name="static")


# Debugging route
@app.get("/debug")
async def debug_route():
    return {
        "message": "Frontend debug route working",
        "wwwroot_path": WWWROOT_PATH,
        "files": os.listdir(WWWROOT_PATH),
    }


# Catch-all route for SPA
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    print(f"Requested path: {full_path}")
    app_html_path = os.path.join(WWWROOT_PATH, "app.html")

    if os.path.exists(app_html_path):
        return FileResponse(app_html_path)
    else:
        return HTMLResponse(
            content=f"app.html not found. Current path: {app_html_path}",
            status_code=404,
        )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)
