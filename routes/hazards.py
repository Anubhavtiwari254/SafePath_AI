import hashlib
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from config import Config
from models import db, HazardReport, ReportConfirmation
from services.image_service import ImageService
from services.geocoding_service import GeocodingService

hazards_bp = Blueprint("hazards", __name__)


@hazards_bp.route("/safety-map")
def safety_map_page():
    """Interactive Unsafe Area Map page."""
    return render_template("safety_map.html", categories=Config.HAZARD_CATEGORIES)


@hazards_bp.route("/report-hazard", methods=["GET", "POST"])
def report_hazard_page():
    """Report an unsafe place page."""
    if request.method == "POST":
        return create_hazard_report()
    return render_template("report_hazard.html", categories=Config.HAZARD_CATEGORIES)


@hazards_bp.route("/api/hazards", methods=["GET"])
def get_hazards_api():
    """Retrieve community-reported hazards with filtering."""
    category = request.args.get("category")
    severity = request.args.get("severity")
    status = request.args.get("status", "all")  # 'verified', 'pending', 'all'
    timeframe = request.args.get("timeframe", "all")  # '24h', '7d', '30d', 'all'

    query = HazardReport.query

    # Status filter
    if status == "verified":
        query = query.filter_by(verification_status="verified")
    elif status == "pending":
        query = query.filter_by(verification_status="pending")
    else:
        # By default exclude rejected reports from public view
        query = query.filter(HazardReport.verification_status != "rejected")

    # Category filter
    if category and category in Config.HAZARD_CATEGORIES:
        query = query.filter_by(category=category)

    # Severity filter
    if severity and severity in ("low", "medium", "high"):
        query = query.filter_by(severity=severity)

    # Timeframe filter
    now = datetime.now(timezone.utc)
    if timeframe == "24h":
        cutoff = now - timedelta(hours=24)
        query = query.filter(HazardReport.incident_datetime >= cutoff)
    elif timeframe == "7d":
        cutoff = now - timedelta(days=7)
        query = query.filter(HazardReport.incident_datetime >= cutoff)
    elif timeframe == "30d":
        cutoff = now - timedelta(days=30)
        query = query.filter(HazardReport.incident_datetime >= cutoff)

    reports = query.order_by(HazardReport.created_at.desc()).limit(200).all()
    return jsonify({
        "success": True,
        "count": len(reports),
        "hazards": [r.to_dict(public_view=True) for r in reports]
    })


@hazards_bp.route("/api/hazards", methods=["POST"])
def create_hazard_report():
    """Submit a new community hazard report."""
    is_json = request.is_json
    data = request.get_json() if is_json else request.form

    try:
        lat = float(data.get("latitude", 0.0))
        lng = float(data.get("longitude", 0.0))
    except (ValueError, TypeError):
        msg = "Valid latitude and longitude coordinates are required."
        return (jsonify({"success": False, "error": msg}), 400) if is_json else (flash(msg, "danger") or redirect(url_for("hazards.report_hazard_page")))

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        msg = "Coordinates are outside of valid range (-90 to 90, -180 to 180)."
        return (jsonify({"success": False, "error": msg}), 400) if is_json else (flash(msg, "danger") or redirect(url_for("hazards.report_hazard_page")))

    category = (data.get("category") or "").strip()
    if category not in Config.HAZARD_CATEGORIES:
        msg = f"Invalid hazard category. Options: {', '.join(Config.HAZARD_CATEGORIES.keys())}"
        return (jsonify({"success": False, "error": msg}), 400) if is_json else (flash(msg, "danger") or redirect(url_for("hazards.report_hazard_page")))

    description = (data.get("description") or "").strip()
    if len(description) < 8 or len(description) > 1000:
        msg = "Description must be between 8 and 1000 characters."
        return (jsonify({"success": False, "error": msg}), 400) if is_json else (flash(msg, "danger") or redirect(url_for("hazards.report_hazard_page")))

    severity = (data.get("severity") or "medium").strip().lower()
    if severity not in ("low", "medium", "high"):
        severity = "medium"

    # Incident date/time parsing
    inc_dt_str = data.get("incident_datetime")
    if inc_dt_str:
        try:
            incident_dt = datetime.fromisoformat(inc_dt_str.replace("Z", "+00:00"))
        except Exception:
            incident_dt = datetime.now(timezone.utc)
    else:
        incident_dt = datetime.now(timezone.utc)

    # Optional photo upload handling
    photo_filename = None
    if "photo" in request.files:
        photo_file = request.files["photo"]
        if photo_file and photo_file.filename:
            try:
                photo_filename = ImageService.save_hazard_photo(photo_file)
            except ValueError as ve:
                msg = str(ve)
                return (jsonify({"success": False, "error": msg}), 400) if is_json else (flash(msg, "danger") or redirect(url_for("hazards.report_hazard_page")))

    # Initial status: Admins get instant verification, users/guests get 'pending'
    status = "verified" if (current_user.is_authenticated and current_user.is_admin) else "pending"
    user_id = current_user.id if current_user.is_authenticated else None

    report = HazardReport(
        user_id=user_id,
        latitude=lat,
        longitude=lng,
        category=category,
        description=description,
        severity=severity,
        incident_datetime=incident_dt,
        verification_status=status,
        photo_path=photo_filename
    )
    db.session.add(report)
    db.session.commit()

    if is_json:
        return jsonify({
            "success": True,
            "message": "Report submitted successfully! Thank you for contributing to community safety.",
            "report": report.to_dict(public_view=True)
        }), 201

    flash("Your report has been submitted and is now queued for verification. Thank you for making our streets safer!", "success")
    return redirect(url_for("hazards.safety_map_page"))


@hazards_bp.route("/api/hazards/<int:report_id>", methods=["GET"])
def get_single_hazard(report_id):
    report = HazardReport.query.get_or_404(report_id)
    return jsonify({
        "success": True,
        "hazard": report.to_dict(public_view=True)
    })


@hazards_bp.route("/api/hazards/<int:report_id>/confirm", methods=["POST"])
def confirm_hazard_report(report_id):
    """Corroborate/confirm an existing hazard to increase verification weight."""
    report = HazardReport.query.get_or_404(report_id)

    # Fingerprint to prevent spam confirmations
    user_id = current_user.id if current_user.is_authenticated else None
    client_ip = request.remote_addr or "unknown"
    client_ident = hashlib.sha256(f"{client_ip}_{report_id}".encode()).hexdigest()[:32]

    # Check if existing confirmation exists
    existing = None
    if user_id:
        existing = ReportConfirmation.query.filter_by(report_id=report_id, user_id=user_id).first()
    else:
        existing = ReportConfirmation.query.filter_by(report_id=report_id, client_identifier=client_ident).first()

    if existing:
        return jsonify({
            "success": False,
            "error": "You have already confirmed this hazard report.",
            "confirmation_count": report.confirmation_count
        }), 400

    new_conf = ReportConfirmation(
        report_id=report_id,
        user_id=user_id,
        client_identifier=client_ident
    )
    db.session.add(new_conf)

    # Auto-verify rule: If an unverified report receives 3 or more community confirmations, mark as verified
    if report.verification_status == "pending" and report.confirmation_count + 1 >= 3:
        report.verification_status = "verified"
        report.moderation_notes = "Auto-verified via community confirmation consensus (3+ confirmations)."

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Hazard confirmed. Thank you for keeping the community updated!",
        "confirmation_count": report.confirmation_count,
        "verification_status": report.verification_status
    })


@hazards_bp.route("/api/hazards/<int:report_id>", methods=["DELETE"])
def delete_hazard_report(report_id):
    """Delete report (author or admin only)."""
    report = HazardReport.query.get_or_404(report_id)

    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    if not (current_user.is_admin or report.user_id == current_user.id):
        return jsonify({"success": False, "error": "Not authorized to delete this report."}), 403

    db.session.delete(report)
    db.session.commit()
    return jsonify({"success": True, "message": "Report deleted successfully."})
