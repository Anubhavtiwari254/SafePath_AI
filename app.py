import os
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify
from flask_login import LoginManager
from config import Config
from models import db, User
from seed_data import seed_database


def create_app(config_class=Config):
    """Application factory for SafePath AI."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this feature."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes import main_bp, auth_bp, route_bp, hazards_bp, emergency_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(route_bp)
    app.register_blueprint(hazards_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(admin_bp)

    # Global context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.now(timezone.utc).year,
            "hazard_categories": Config.HAZARD_CATEGORIES,
            "severity_levels": Config.SEVERITY_LEVELS
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(e):
        if app.template_context_processors:
            return render_template("base.html", error_title="403 - Forbidden", error_message="You do not have administrative permissions to view this resource."), 403
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template("base.html", error_title="404 - Not Found", error_message="The requested page could not be located."), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("base.html", error_title="500 - Server Error", error_message="An unexpected server error occurred. Please try again shortly."), 500

    # Auto-initialize database tables and demo seed data if needed
    with app.app_context():
        db.create_all()
        # Seed if empty
        if User.query.count() == 0:
            seed_database(app)

    # CLI command to manually re-seed
    @app.cli.command("seed")
    def seed_cmd():
        """Seed initial demonstration hazards and demo user."""
        seed_database(app)
        print("Database seeding completed.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
