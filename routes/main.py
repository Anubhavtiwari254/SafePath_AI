from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
from config import Config
from models import HazardReport, TrustedContact, EmergencyShare

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Home page with hero section, quick search, feature showcase, and statistics."""
    total_hazards = HazardReport.query.filter(HazardReport.verification_status != "rejected").count()
    verified_hazards = HazardReport.query.filter_by(verification_status="verified").count()
    return render_template(
        "index.html",
        categories=Config.HAZARD_CATEGORIES,
        total_hazards=total_hazards,
        verified_hazards=verified_hazards
    )


@main_bp.route("/about")
def about():
    """About & Safety Disclaimer page."""
    return render_template("about.html", categories=Config.HAZARD_CATEGORIES)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """User personal dashboard with contacts, reports, and active SOS shares."""
    my_reports = HazardReport.query.filter_by(user_id=current_user.id).order_by(HazardReport.created_at.desc()).all()
    my_contacts = TrustedContact.query.filter_by(user_id=current_user.id).order_by(TrustedContact.created_at.desc()).all()
    my_shares = EmergencyShare.query.filter_by(user_id=current_user.id).order_by(EmergencyShare.created_at.desc()).limit(10).all()

    return render_template(
        "dashboard.html",
        reports=my_reports,
        contacts=my_contacts,
        shares=my_shares,
        categories=Config.HAZARD_CATEGORIES
    )
