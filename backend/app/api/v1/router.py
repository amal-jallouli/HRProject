"""Agrégation des routes de l'API v1."""

from fastapi import APIRouter

<<<<<<< HEAD
#from app.api.v1 import catalogue, health, programs
from app.api.v1 import catalogue, health, programs, visitor_sessions
=======
from app.api.v1 import catalogue, health, programs

>>>>>>> f768d88d53bdd019ee98eeb8ce8ba5af5f7a1e3d
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(catalogue.router)
api_router.include_router(programs.router)
<<<<<<< HEAD
api_router.include_router(visitor_sessions.router)
=======
>>>>>>> f768d88d53bdd019ee98eeb8ce8ba5af5f7a1e3d
