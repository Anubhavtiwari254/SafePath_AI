import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint("auth", __name__)


def is_valid_email(email: str) -> bool:
    regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(regex, email))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # Handle both JSON and Form submission
        if request.is_json:
            data = request.get_json() or {}
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            remember = bool(data.get("remember", False))
        else:
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            remember = bool(request.form.get("remember"))

        if not email or not password:
            msg = "Email and password are required."
            if request.is_json:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            msg = "Invalid email or password."
            if request.is_json:
                return jsonify({"success": False, "error": msg}), 401
            flash(msg, "danger")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        if request.is_json:
            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": user.to_dict(),
                "redirect": url_for("main.dashboard")
            }), 200

        flash(f"Welcome back, {user.name}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json() or {}
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
        else:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

        # Validation
        if not name or len(name) < 2:
            msg = "Please enter your full name (at least 2 characters)."
            if request.is_json:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return render_template("auth/register.html")

        if not is_valid_email(email):
            msg = "Please provide a valid email address."
            if request.is_json:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            msg = "Password must be at least 6 characters long."
            if request.is_json:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            msg = "An account with this email already exists."
            if request.is_json:
                return jsonify({"success": False, "error": msg}), 409
            flash(msg, "danger")
            return render_template("auth/register.html")

        new_user = User(name=name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        if request.is_json:
            return jsonify({
                "success": True,
                "message": "Account created successfully.",
                "user": new_user.to_dict(),
                "redirect": url_for("main.dashboard")
            }), 201

        flash("Welcome to SafePath AI! Your account was created successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


# JSON API Auth Endpoints (for programmatic client interactions)
@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    return login()


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    return register()


@auth_bp.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


@auth_bp.route("/api/profile", methods=["GET"])
@login_required
def api_profile():
    return jsonify({
        "success": True,
        "user": current_user.to_dict(),
        "contacts": [c.to_dict() for c in current_user.trusted_contacts]
    })


@auth_bp.route("/api/profile/delete", methods=["POST"])
@login_required
def delete_account():
    """Privacy: full account and personal data deletion."""
    user = current_user
    logout_user()
    db.session.delete(user)
    db.session.commit()

    if request.is_json:
        return jsonify({"success": True, "message": "Account and associated data deleted permanently."})
    flash("Your account and associated personal data have been completely removed.", "info")
    return redirect(url_for("main.index"))
