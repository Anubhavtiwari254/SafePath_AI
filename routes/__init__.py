from flask import Blueprint

# Blueprints
from .main import main_bp
from .auth import auth_bp
from .route_finder import route_bp
from .hazards import hazards_bp
from .emergency import emergency_bp
from .admin import admin_bp

__all__ = [
    "main_bp",
    "auth_bp",
    "route_bp",
    "hazards_bp",
    "emergency_bp",
    "admin_bp"
]
