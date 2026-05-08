import pytest
from flask import g
from flask import session

from flaskr.db import get_db

from flask_login import current_user

from flaskr.models import User
from flaskr.extensions import db_SQLAlchemy
from sqlalchemy import select

def _test_register_location(client):
    response = client.get("/auth/register")

    print(response.status_code)
    print(response.location)
    print(response.headers)

    assert False

def test_register(client, app):
    # 1. Test that the registration page loads
    # Note: If this gives a 302, ensure Talisman force_https is False in tests
    assert client.get("/auth/register").status_code == 200

    # 2. Test successful registration
    # Based on your auth.py, registration calls login_user and redirects to index ('/')
    response = client.post("/auth/register", data={"username": "newuser", "password": "password123"})
    if response.status_code == 200:
        # This will print the HTML of the page. 
        # Look for "flash" messages like "User already registered"
        print(response.data.decode('utf-8'))
    print(f"Response location: {response.headers.get('Location')}")
    
    # Check if it redirects to the index page (your current logic)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # 3. Test that the user was inserted into the database using SQLAlchemy
    with app.app_context():
        user = db_SQLAlchemy.session.execute(
            select(User).where(User.username == "newuser")
        ).scalar()
        
        assert user is not None
        assert user.username == "newuser"


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("", "", b"Username is required."),
        ("a", "", b"Password is required."),
        ("test", "test", b"already registered"),
    ),
)
def test_register_validate_input(client, username, password, message):
    response = client.post(
        "/auth/register", data={"username": username, "password": password}
    )
    assert message in response.data

def test_login(client, auth):
    # 1. Test that the login page loads (200 OK)
    # If this still gives 302, ensure Talisman force_https=(not app.testing)
    assert client.get("/auth/login").status_code == 200

    # 2. Test successful login redirect
    # auth.login() uses client.post('/auth/login', ...)
    response = auth.login(username="test", password="test")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # 3. Verify user state using 'with client' to access the request context
    with client:
        # Trigger a request so the session is loaded and current_user is populated
        client.get("/")
        
        # Flask-Login stores the user ID as a string in "_user_id"
        assert session["_user_id"] == "1"
        
        # Verify the current_user object properties
        assert current_user.is_authenticated
        assert current_user.username == "test"
        assert current_user.id == 1


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("a", "test", b"Incorrect username or password."), 
        ("test", "a", b"Incorrect username or password.")
    ),
)
def test_login_validate_input(auth, username, password, message):
    # When validation fails, the app returns 200 (re-renders the login page)
    # instead of redirecting (302).
    response = auth.login(username, password)
    assert response.status_code == 200
    assert message in response.data


def test_logout(client, auth):
    auth.login()

    with client:
        # Initial check to ensure we are logged in
        client.get("/")
        assert session.get("_user_id") is not None
        assert current_user.is_authenticated

        # Perform logout
        auth.logout()
        
        # Flask-Login removes '_user_id' from the session on logout
        assert "_user_id" not in session
        assert current_user.is_anonymous