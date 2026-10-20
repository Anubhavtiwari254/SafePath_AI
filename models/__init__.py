from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User, TrustedContact
from .hazard import HazardReport, ReportConfirmation
from .emergency import EmergencyShare, ModerationLog

__all__ = [
    "db",
    "User",
    "TrustedContact",
    "HazardReport",
    "ReportConfirmation",
    "EmergencyShare",
    "ModerationLog",
]
