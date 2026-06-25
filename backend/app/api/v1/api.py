"""Aggregate v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, health, shift_types, teams

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(shift_types.router)
api_router.include_router(teams.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
