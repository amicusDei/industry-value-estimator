"""
FastAPI backend for the AI Industry Value Estimator.

Serves pipeline outputs (forecasts, segments, companies, diagnostics) as a
JSON API consumed by the Next.js Bloomberg-style frontend.

Run with:
    uv run uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import forecasts, segments, companies, diagnostics, export, sensitivity, total, consensus

app = FastAPI(
    title="AI Industry Value Estimator API",
    version="1.1.0",
    description="JSON API serving AI market size forecasts, company attribution, and backtesting diagnostics.",
)

# CORS for Next.js frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(forecasts.router)
app.include_router(segments.router)
app.include_router(companies.router)
app.include_router(diagnostics.router)
app.include_router(export.router)
app.include_router(sensitivity.router)
app.include_router(total.router)
app.include_router(consensus.router)


@app.get("/")
def root():
    return {
        "name": "AI Industry Value Estimator API",
        "version": "1.1.0",
        "endpoints": [
            "/api/v1/forecasts",
            "/api/v1/segments",
            "/api/v1/companies",
            "/api/v1/diagnostics",
            "/api/v1/export/csv",
            "/api/v1/export/excel",
            "/api/v1/sensitivity",
        ],
    }
