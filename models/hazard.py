from datetime import datetime, timezone
from . import db


class HazardReport(db.Model):
    """Community-submitted hazard report."""
    __tablename__ = "hazard_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    latitude = db.Column(db.Float, nullable=False, index=True)
    longitude = db.Column(db.Float, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default="medium", nullable=False)  # 'low', 'medium', 'high'
    incident_datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    verification_status = db.Column(db.String(20), default="pending", nullable=False, index=True)  # 'pending', 'verified', 'rejected'
    photo_path = db.Column(db.String(255), nullable=True)
    moderation_notes = db.Column(db.Text, nullable=True)

    # Relationships
    confirmations = db.relationship("ReportConfirmation", backref="report", cascade="all, delete-orphan", lazy="dynamic")
    moderation_logs = db.relationship("ModerationLog", backref="report", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def confirmation_count(self) -> int:
        return self.confirmations.count()

    def to_dict(self, public_view: bool = True) -> dict:
        """Serialize report with privacy protection for public views."""
        data = {
            "id": self.id,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "incident_datetime": self.incident_datetime.isoformat() if self.incident_datetime else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verification_status": self.verification_status,
            "confirmation_count": self.confirmation_count,
            "has_photo": bool(self.photo_path),
            "photo_url": f"/static/uploads/{self.photo_path}" if self.photo_path else None
        }

        if not public_view:
            data.update({
                "user_id": self.user_id,
                "moderation_notes": self.moderation_notes,
                "author_email": self.author.email if self.author else "Anonymous / Guest",
                "author_name": self.author.name if self.author else "Guest Reporter"
            })
        return data


class ReportConfirmation(db.Model):
    """Community confirmation/corroboration of a hazard."""
    __tablename__ = "report_confirmations"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("hazard_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    client_identifier = db.Column(db.String(64), nullable=True, index=True)  # Hashed session/IP to limit spam confirmations
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("report_id", "user_id", name="uq_report_user"),
    )
