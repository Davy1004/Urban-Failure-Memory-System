from fastapi import APIRouter

from app.api.v1 import auth, dashboard, health, locations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(locations.router)

# The four dashboard screens (NEXT.md, 8 Sep 2026).
api_router.include_router(dashboard.index_router)
api_router.include_router(dashboard.watchlist_router)
api_router.include_router(dashboard.emerging_router)
api_router.include_router(dashboard.allocation_router)

# Phase 3+ routers land here: triage, patterns, interventions.
