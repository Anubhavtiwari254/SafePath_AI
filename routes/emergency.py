import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import current_user, login_required
from config import Config
from models import db, EmergencyShare, TrustedContact
from services.notification_service import NotificationService
from services.geocoding_service import GeocodingService

emergency_bp = Blueprint("emergency", __name__)


def hash_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of raw sharing token."""
    return hashlib.sha256(raw_token.strip().encode()).hexdigest()


@emergency_bp.route("/emergency")
def emergency_page():
    """Emergency Center hub with SOS trigger, contacts, and directory."""
    contacts = []
    if current_user.is_authenticated:
        contacts = TrustedContact.query.filter_by(user_id=current_user.id).order_by(TrustedContact.created_at.desc()).all()

    directory = Config.EMERGENCY_DIRECTORIES.get("universal", [])
    return render_template(
        "emergency.html",
        contacts=contacts,
        directory=directory
    )


@emergency_bp.route("/emergency/share/<token>")
def emergency_share_view(token):
    """Public / recipient emergency tracking page."""
    token_h = hash_token(token)
    share = EmergencyShare.query.filter_by(token_hash=token_h).first()

    if not share:
        return render_template("emergency_view.html", error="Invalid or non-existent emergency sharing link.", share=None), 404

    if not share.is_active:
        msg = "This emergency location link was revoked by the user." if share.revoked_at else "This emergency sharing session has expired."
        return render_template("emergency_view.html", error=msg, share=share), 410

    # Reverse geocode location for responder clarity
    approx_address = GeocodingService.reverse(share.current_lat, share.current_lng)

    return render_template(
        "emergency_view.html",
        share=share,
        raw_token=token,
        approx_address=approx_address,
        error=None
    )


# --- Emergency REST APIs ---

@emergency_bp.route("/api/emergency/share", methods=["POST"])
def activate_emergency_share():
    """
    Activate SOS: record location, create revocable time-limited token,
    and dispatch notification payload to trusted contacts.
    """
    data = request.get_json() or {}
    try:
        lat = float(data.get("latitude"))
        lng = float(data.get("longitude"))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Valid latitude and longitude are required."}), 400

    accuracy = data.get("accuracy_meters")
    if accuracy is not None:
        try:
            accuracy = float(accuracy)
        except ValueError:
            accuracy = None

    user_message = data.get("message") or "Emergency SOS activated. Please check my location immediately."

    # Generate 64-char cryptographically secure token
    raw_token = secrets.token_hex(32)
    token_h = hash_token(raw_token)

    # Valid for 6 hours
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=6)

    user_id = current_user.id if current_user.is_authenticated else None
    sender_name = current_user.name if current_user.is_authenticated else "SafePath AI User"

    share_record = EmergencyShare(
        user_id=user_id,
        token_hash=token_h,
        current_lat=lat,
        current_lng=lng,
        accuracy_meters=accuracy,
        message=user_message,
        created_at=now,
        expires_at=expires_at
    )
    db.session.add(share_record)
    db.session.commit()

    # Generate complete sharing URL
    share_url = url_for("emergency.emergency_share_view", token=raw_token, _external=True)

    # Collect recipient contacts
    contacts_list = []
    if current_user.is_authenticated:
        user_contacts = TrustedContact.query.filter_by(user_id=current_user.id).all()
        contacts_list = [c.to_dict() for c in user_contacts]

    # Dispatch alerts through Notification Service
    dispatch_result = NotificationService.dispatch_emergency_alert(
        contacts=contacts_list,
        sender_name=sender_name,
        share_url=share_url,
        coordinates={"latitude": lat, "longitude": lng},
        custom_message=user_message
    )

    return jsonify({
        "success": True,
        "token": raw_token,
        "share_id": share_record.id,
        "share_url": share_url,
        "expires_at": expires_at.isoformat(),
        "notification_summary": dispatch_result.get("summary"),
        "is_simulated": dispatch_result.get("is_simulated", True),
        "native_sms_url": dispatch_result.get("native_sms_url"),
        "whatsapp_url": dispatch_result.get("whatsapp_url"),
        "delivery_results": dispatch_result.get("delivery_results", [])
    }), 201


@emergency_bp.route("/api/emergency/revoke", methods=["POST"])
def revoke_emergency_share():
    """Revoke an active emergency share token."""
    data = request.get_json() or {}
    token = data.get("token")
    share_id = data.get("share_id")

    share = None
    if token:
        token_h = hash_token(token)
        share = EmergencyShare.query.filter_by(token_hash=token_h).first()
    elif share_id:
        share = EmergencyShare.query.get(share_id)

    if not share:
        return jsonify({"success": False, "error": "Share record not found."}), 404

    # Authorization: if logged in user owns it, or matching raw token presented
    if share.user_id and current_user.is_authenticated and share.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    share.revoked_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Emergency location sharing has been permanently deactivated."
    })


@emergency_bp.route("/api/emergency/location/<token>", methods=["GET"])
def get_emergency_location_api(token):
    """API for the emergency view map to poll/retrieve location status."""
    token_h = hash_token(token)
    share = EmergencyShare.query.filter_by(token_hash=token_h).first()

    if not share:
        return jsonify({"success": False, "error": "Invalid token"}), 404

    if not share.is_active:
        return jsonify({
            "success": False,
            "error": "Link expired or revoked",
            "is_active": False,
            "revoked": share.revoked_at is not None
        }), 410

    return jsonify({
        "success": True,
        "share": share.to_dict(include_sensitive=True)
    })


# --- Trusted Contacts APIs ---

@emergency_bp.route("/api/contacts", methods=["GET"])
@login_required
def get_contacts_api():
    contacts = TrustedContact.query.filter_by(user_id=current_user.id).order_by(TrustedContact.created_at.desc()).all()
    return jsonify({
        "success": True,
        "contacts": [c.to_dict() for c in contacts]
    })


@emergency_bp.route("/api/contacts", methods=["POST"])
@login_required
def add_contact_api():
    data = request.get_json() or {}
    name = (data.get("contact_name") or "").strip()
    method = (data.get("contact_method") or "phone").strip().lower()
    value = (data.get("contact_value") or "").strip()

    if not name or len(name) < 2:
        return jsonify({"success": False, "error": "Contact name is required (min 2 characters)."}), 400

    if not value or len(value) < 4:
        return jsonify({"success": False, "error": "Contact phone number or email is required."}), 400

    # Limit to 5 contacts per user
    current_count = TrustedContact.query.filter_by(user_id=current_user.id).count()
    if current_count >= 10:
        return jsonify({"success": False, "error": "Maximum of 10 trusted contacts allowed per account."}), 400

    new_contact = TrustedContact(
        user_id=current_user.id,
        contact_name=name,
        contact_method=method,
        contact_value=value
    )
    db.session.add(new_contact)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Trusted contact added successfully.",
        "contact": new_contact.to_dict()
    }), 201


@emergency_bp.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def delete_contact_api(contact_id):
    contact = TrustedContact.query.filter_by(id=contact_id, user_id=current_user.id).first_or_404()
    db.session.delete(contact)
    db.session.commit()
    return jsonify({"success": True, "message": "Contact removed successfully."})


@emergency_bp.route("/api/emergency/directory", methods=["GET"])
def get_emergency_directory_api():
    return jsonify({
        "success": True,
        "directory": Config.EMERGENCY_DIRECTORIES.get("universal", [])
    })
