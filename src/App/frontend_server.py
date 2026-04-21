import os

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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

# Proxy configuration for WAF/private networking deployments
PROXY_API_REQUESTS = os.getenv("PROXY_API_REQUESTS", "false").lower() == "true"
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# Serve static files from build directory
app.mount(
    "/assets", StaticFiles(directory=os.path.join(BUILD_DIR, "assets")), name="assets"
)


@app.get("/")
async def serve_index():
    return FileResponse(INDEX_HTML)


@app.get("/config")
async def get_config():
    auth_enabled = os.getenv("AUTH_ENABLED", "false")

    if PROXY_API_REQUESTS:
        # WAF mode: frontend proxies API calls, so tell browser to use same origin
        api_url = "/api"
    else:
        # Non-WAF mode: browser calls backend directly
        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
        api_url = backend_url + "/api"

    config = {
        "API_URL": api_url,
        "ENABLE_AUTH": auth_enabled,
    }
    return config


@app.get("/health")
async def health():
    return {"status": "healthy"}


# API proxy routes for WAF/private networking deployments
if PROXY_API_REQUESTS:

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_api(request: Request, path: str):
        """Proxy API requests to the private backend over VNet."""
        target_url = f"{BACKEND_API_URL}/api/{path}"
        query_string = str(request.query_params)
        if query_string:
            target_url = f"{target_url}?{query_string}"

        headers = dict(request.headers)
        headers.pop("host", None)

        body = await request.body()

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            headers=dict(response.headers),
        )


@app.get("/{full_path:path}")
async def serve_app(full_path: str):
    # Remediation: normalize and check containment before serving
    file_path = os.path.normpath(os.path.join(BUILD_DIR, full_path))
    # Block traversal and dotfiles
    if (
        not file_path.startswith(BUILD_DIR)
        or ".." in full_path
        or "/." in full_path
        or "\\." in full_path
    ):
        return FileResponse(INDEX_HTML)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(INDEX_HTML)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000, access_log=False, log_level="info")
