import os
import tempfile
import pytest

from flaskr import create_app
from flaskr.extensions import db_SQLAlchemy  # Import your SQLAlchemy instance
from flaskr.db import init_db  # Keep if you still use it for non-SQLAlchemy parts

# Read in SQL for populating test data
with open(os.path.join(os.path.dirname(__file__), "data.sql"), "rb") as f:
    _data_sql = f.read().decode("utf8")

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        "TESTING": True, 
        "DATABASE": db_path,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
    })

    with app.app_context():
        db_SQLAlchemy.create_all()
        with db_SQLAlchemy.engine.connect() as connection:
            raw_conn = connection.connection
            raw_conn.executescript(_data_sql)
            connection.commit()

    yield app

    # --- CLEANUP PHASE ---
    with app.app_context():
        # 1. This is the critical part: shut down the engine pool
        db_SQLAlchemy.engine.dispose()
    
    # 2. Close the file descriptor
    os.close(db_fd)
    
    # 3. Now Windows will allow you to delete it
    os.unlink(db_path)
    
@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, username="test", password="test"):
        # Note: Added 'follow_redirects=False' to ensure you get the 302 for testing
        return self._client.post(
            "/auth/login", 
            data={"username": username, "password": password},
            follow_redirects=False 
        )

    def logout(self):
        return self._client.get("/auth/logout")

@pytest.fixture
def auth(client):
    return AuthActions(client)