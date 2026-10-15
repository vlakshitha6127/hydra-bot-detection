"""
Main FastAPI Application Entrypoint for BreachX / HYDRA.
Serves both the REST API and the built React Dashboard.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.api.routes import router

app = FastAPI(
    title="BreachX 2026 / HYDRA: Coordinated Bot Network Detection",
    description=(
        "Autonomous Cybersecurity Platform for Coordinated Bot Network Detection. "
        "Implements multi-evidence non-compensatory gates, graduated response ladder, "
        "cryptographic tamper-evident hash chaining, and exact counterfactual explainability."
    ),
    version="1.7.0",
)

# Enable CORS for Vite React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API router under /api
app.include_router(router)

# Mount built React frontend if dist directory exists
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "title": "BreachX 2026 / HYDRA Detection Engine",
            "status": "operational",
            "documentation": "/docs",
            "api_root": "/api",
            "notice": "All metrics and populations are synthetic-data results.",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
