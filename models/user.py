from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(UserMixin, db.Model):
    """User model with secure password hashing and relationship to reports and contacts."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    trusted_contacts = db.relationship("TrustedContact", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    hazard_reports = db.relationship("HazardReport", backref="author", foreign_keys="HazardReport.user_id", lazy="dynamic")
    emergency_shares = db.relationship("EmergencyShare", backref="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and store user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify plain password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "contacts_count": self.trusted_contacts.count()
        }


class TrustedContact(db.Model):
    """Emergency contacts configured by user."""
    __tablename__ = "trusted_contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_name = db.Column(db.String(120), nullable=False)
    contact_method = db.Column(db.String(20), default="phone", nullable=False)  # 'phone', 'email', 'sms'
    contact_value = db.Column(db.String(150), nullable=False)  # phone number or email address
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "contact_name": self.contact_name,
            "contact_method": self.contact_method,
            "contact_value": self.contact_value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
