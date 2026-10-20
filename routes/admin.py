from functools import wraps
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import current_user, login_required
from config import Config
from models import db, HazardReport, ModerationLog, User

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/admin")
@login_required
@admin_required
def admin_dashboard_page():
    """Admin Moderation and Safety Analytics Dashboard."""
    total_reports = HazardReport.query.count()
    pending_count = HazardReport.query.filter_by(verification_status="pending").count()
    verified_count = HazardReport.query.filter_by(verification_status="verified").count()
    rejected_count = HazardReport.query.filter_by(verification_status="rejected").count()

    recent_logs = ModerationLog.query.order_by(ModerationLog.created_at.desc()).limit(15).all()

    return render_template(
        "admin.html",
        total_reports=total_reports,
        pending_count=pending_count,
        verified_count=verified_count,
        rejected_count=rejected_count,
        categories=Config.HAZARD_CATEGORIES,
        logs=recent_logs
    )


@admin_bp.route("/api/admin/reports", methods=["GET"])
@login_required
@admin_required
def get_admin_reports():
    """Retrieve full reports for moderation with unmasked author data."""
    status = request.args.get("status")
    category = request.args.get("category")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    query = HazardReport.query

    if status and status in ("pending", "verified", "rejected"):
        query = query.filter_by(verification_status=status)

    if category and category in Config.HAZARD_CATEGORIES:
        query = query.filter_by(category=category)

    paginated = query.order_by(HazardReport.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "total": paginated.total,
        "pages": paginated.pages,
        "current_page": paginated.page,
        "reports": [r.to_dict(public_view=False) for r in paginated.items]
    })


@admin_bp.route("/api/admin/reports/<int:report_id>", methods=["PATCH"])
@login_required
@admin_required
def moderate_report(report_id):
    """Verify, reject, or adjust severity of a community report."""
    report = HazardReport.query.get_or_404(report_id)
    data = request.get_json() or {}

    new_status = data.get("verification_status")
    new_severity = data.get("severity")
    notes = data.get("moderation_notes")

    actions_taken = []

    if new_status and new_status in ("pending", "verified", "rejected"):
        if report.verification_status != new_status:
            actions_taken.append(f"status changed from '{report.verification_status}' to '{new_status}'")
            report.verification_status = new_status

    if new_severity and new_severity in ("low", "medium", "high"):
        if report.severity != new_severity:
            actions_taken.append(f"severity changed from '{report.severity}' to '{new_severity}'")
            report.severity = new_severity

    if notes is not None:
        report.moderation_notes = notes

    if actions_taken:
        action_summary = "; ".join(actions_taken)
        log_entry = ModerationLog(
            admin_user_id=current_user.id,
            report_id=report.id,
            action=action_summary,
            notes=notes
        )
        db.session.add(log_entry)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Report successfully updated.",
        "report": report.to_dict(public_view=False)
    })


@admin_bp.route("/api/admin/reports/<int:report_id>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_report(report_id):
    """Remove spam or malicious reports."""
    report = HazardReport.query.get_or_404(report_id)

    log_entry = ModerationLog(
        admin_user_id=current_user.id,
        report_id=report.id,
        action="deleted_report",
        notes=f"Permanently deleted hazard #{report.id} ({report.category})"
    )
    db.session.add(log_entry)
    db.session.delete(report)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Report #{report_id} permanently removed."
    })


@admin_bp.route("/api/admin/analytics", methods=["GET"])
@login_required
@admin_required
def get_analytics():
    """Summary analytics for admin charts."""
    # Category counts
    category_counts = {}
    for cat_key in Config.HAZARD_CATEGORIES:
        count = HazardReport.query.filter_by(category=cat_key).count()
        category_counts[cat_key] = count

    # Status counts
    status_counts = {
        "pending": HazardReport.query.filter_by(verification_status="pending").count(),
        "verified": HazardReport.query.filter_by(verification_status="verified").count(),
        "rejected": HazardReport.query.filter_by(verification_status="rejected").count()
    }

    # Total users
    users_count = User.query.count()

    return jsonify({
        "success": True,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "total_users": users_count,
        "total_reports": sum(status_counts.values())
    })
