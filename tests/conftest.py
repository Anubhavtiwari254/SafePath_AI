import pytest
from app import create_app
from config import Config
from models import db, User, HazardReport, TrustedContact


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_user(app):
    with app.app_context():
        user = User(name="Test User", email="tester@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "password": "password123"
        }


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = User(name="Admin Moderator", email="mod@example.com", is_admin=True)
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()
        return {
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "password": "adminpass123"
        }
