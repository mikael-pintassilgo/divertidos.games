import pytest
from flaskr.models import User, Role
from flaskr.extensions import db_SQLAlchemy

def test_add_index_roles(client, auth, app):
    # 1. Test Anonymous User: Should see login/register, NOT the button
    response = client.get("/games/")
    assert b"Log In" in response.data
    assert b"Register" in response.data
    assert b"Import game" not in response.data

    # 2. Test Regular Authenticated User: Should NOT see the button
    # Assuming 'other' in your data.sql is a regular user without admin role
    auth.login(username="other", password="test_password") 
    response = client.get("/games/")
    assert b"Import game" not in response.data
    auth.logout()

    # 3. Test Admin User: SHOULD see the button
    # We ensure the 'test' user has the 'admin' role in the test database
    with app.app_context():
        admin_user = User.query.filter_by(username="test").first()
        admin_role = Role.query.filter_by(name="admin").first()
        if admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
            db_SQLAlchemy.session.commit()

    auth.login(username="test", password="test")
    
    response = client.get("/games/")
    assert b"Log Out" in response.data
    
    print("response.data:", response.data.decode('utf-8'))  # Debug: Print the HTML content
    
    # Check for the button (case-sensitive depending on your HTML)
    assert b"import game".lower() in response.data.lower()
    assert b"add game".lower() in response.data.lower()