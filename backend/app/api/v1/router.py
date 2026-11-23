"""Agrégation des routes de l'API v1."""

from fastapi import APIRouter

from app.api.v1 import catalogue, health, programs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(catalogue.router)
api_router.include_router(programs.router)
