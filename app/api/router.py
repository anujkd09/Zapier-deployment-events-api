"""Aggregate all route modules into a single ``api_router``."""

from fastapi import APIRouter

from app.api import deployments

api_router = APIRouter()
api_router.include_router(deployments.router)
