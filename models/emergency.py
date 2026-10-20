from datetime import datetime, timezone
from . import db


class EmergencyShare(db.Model):
    """Secure, time-limited emergency location sharing token."""
    __tablename__ = "emergency_shares"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)  # SHA-256 hash of token
    current_lat = db.Column(db.Float, nullable=False)
    current_lng = db.Column(db.Float, nullable=False)
    accuracy_meters = db.Column(db.Float, nullable=True)
    message = db.Column(db.String(255), default="Emergency SOS activated. Please check my location.", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_active(self) -> bool:
        """Check if share token is currently valid, unexpired and unrevoked."""
        if self.revoked_at is not None:
            return False
        now = datetime.now(timezone.utc)
        # Ensure comparison is timezone-aware
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now < exp

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "current_lat": self.current_lat,
            "current_lng": self.current_lng,
            "accuracy_meters": self.accuracy_meters,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "revoked": self.revoked_at is not None
        }
        if include_sensitive and self.user:
            data["user_name"] = self.user.name
        return data


class ModerationLog(db.Model):
    """Audit log for all moderation actions taken by administrators."""
    __tablename__ = "moderation_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("hazard_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)  # 'verify', 'reject', 'delete', 'update_severity', 'edit_notes'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    admin = db.relationship("User", foreign_keys=[admin_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_user_id": self.admin_user_id,
            "admin_name": self.admin.name if self.admin else "System / Deleted Admin",
            "report_id": self.report_id,
            "action": self.action,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
