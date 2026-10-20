import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """SafePath AI Application Configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "safepath-insecure-dev-secret-key-change-me")
    
    # Database: Use DATABASE_URL if provided (e.g. Supabase, Neon Postgres),
    # otherwise fallback to /tmp on Vercel or local sqlite file for local dev.
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        if os.getenv("VERCEL"):
            db_url = "sqlite:////tmp/safepath.db"
        else:
            db_url = f"sqlite:///{BASE_DIR / 'safepath.db'}"
    # Handle older postgres:// format for SQLAlchemy compatibility
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration: Vercel serverless filesystem is read-only except /tmp
    if os.getenv("VERCEL"):
        UPLOAD_FOLDER = Path("/tmp") / "uploads"
    else:
        UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5MB max
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    
    # External APIs
    OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
    NOMINATIM_BASE_URL = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
    
    # Notification & Emergency
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "mock")  # 'mock', 'twilio'
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Hazard configuration constants
    HAZARD_CATEGORIES = {
        "broken_streetlights": {
            "label": "Broken or Non-functional Streetlights",
            "icon": "fa-lightbulb",
            "color": "#f59e0b",  # Amber
            "base_penalty": 12,
            "badge_class": "bg-warning text-dark"
        },
        "isolated_areas": {
            "label": "Isolated or Poorly Monitored Areas",
            "icon": "fa-eye-slash",
            "color": "#8b5cf6",  # Purple
            "base_penalty": 16,
            "badge_class": "bg-purple text-white"
        },
        "road_damage": {
            "label": "Road Damage and Potholes",
            "icon": "fa-triangle-exclamation",
            "color": "#f97316",  # Orange
            "base_penalty": 10,
            "badge_class": "bg-orange text-white"
        },
        "suspicious_activity": {
            "label": "Suspicious Activity",
            "icon": "fa-shield-halved",
            "color": "#ef4444",  # Red
            "base_penalty": 20,
            "badge_class": "bg-danger text-white"
        },
        "harassment": {
            "label": "Harassment or Threatening Behavior",
            "icon": "fa-hand-dots",
            "color": "#dc2626",  # Deep Red
            "base_penalty": 24,
            "badge_class": "bg-danger text-white"
        },
        "blocked_road": {
            "label": "Blocked Roads or Unsafe Construction",
            "icon": "fa-road-barrier",
            "color": "#d97706",  # Dark Amber
            "base_penalty": 14,
            "badge_class": "bg-warning text-dark"
        },
        "other_concern": {
            "label": "Other Safety Concerns",
            "icon": "fa-circle-info",
            "color": "#0ea5e9",  # Sky Blue
            "base_penalty": 8,
            "badge_class": "bg-info text-dark"
        }
    }

    SEVERITY_LEVELS = {
        "low": {"multiplier": 0.6, "label": "Low Concern", "badge": "badge-soft-info"},
        "medium": {"multiplier": 1.0, "label": "Medium Risk", "badge": "badge-soft-warning"},
        "high": {"multiplier": 1.6, "label": "High Hazard", "badge": "badge-soft-danger"}
    }

    # Emergency Services Directory (Global fallback + common regional numbers)
    EMERGENCY_DIRECTORIES = {
        "universal": [
            {"service": "Police Emergency", "number": "112", "alt": "911", "desc": "Immediate law enforcement & life safety"},
            {"service": "Ambulance / Medical", "number": "112", "alt": "108", "desc": "Paramedics & emergency health response"},
            {"service": "Fire Rescue", "number": "112", "alt": "101", "desc": "Fire, structural collapse, hazards"},
            {"service": "Women Safety Helpline", "number": "1091", "alt": "181", "desc": "24/7 dedicated support & transit safety"},
            {"service": "Disaster Helpline", "number": "1070", "alt": "1077", "desc": "Natural disasters & localized emergency"}
        ]
    }
