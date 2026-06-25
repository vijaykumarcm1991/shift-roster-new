"""Aggregate v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, shift_types, teams

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(shift_types.router)
api_router.include_router(teams.router)
