import pytest
from flaskr.models import User, Role, Game
from flaskr.extensions import db_SQLAlchemy

import pytest

def test_games_index_anonymous_user(client):
    """Anonymous users should see login/register, NOT the import button."""
    response = client.get("/games/")
    
    assert b"Log In" in response.data
    assert b"Register" in response.data
    assert b"Import game" not in response.data

def test_games_index_regular_user(regular_client):
    """Regular users should not see the import button."""
    response = regular_client.get("/games/")
    
    assert b"Import game" not in response.data

def test_games_index_admin_user(admin_client):
    """Admin users should see the admin buttons and log out option."""
    response = admin_client.get("/games/")
    
    assert b"Log Out" in response.data
    
    # Lowercase decoding helper for cleaner assertions
    html_content = response.data.lower()
    assert b"import game" in html_content
    assert b"add game" in html_content
    
def test_create_game_as_admin(admin_client, app):
    """An admin user should be able to successfully create a game."""
    # 1. Submit the form data to create a game
    response = admin_client.post(
        "/games/create",
        data={"title": "Super Mario Bros", "body": "Classic platformer game"},
        follow_redirects=True
    )
    
    # 2. Assert the request succeeded (redirected back to index or details)
    assert response.status_code == 200
    assert b"Super Mario Bros" in response.data

    # 3. Double check the database to ensure it actually saved
    with app.app_context():
        game = Game.query.filter_by(title="Super Mario Bros").first()
        assert game is not None
        assert game.body == "Classic platformer game"

def test_delete_game_as_admin(admin_client, app):
    """An admin user should be able to delete an existing game."""
    # 1. Arrange: Fetch an existing user to act as the author, then insert the test game
    with app.app_context():
        # Look up the "test" user (or whichever user exists in your data.sql)
        test_user = User.query.filter_by(username="test").first()
        
        # Ensure your model instantiation passes the author_id
        test_game = Game(
            title="Temporary Game", 
            body="To be deleted",
            author_id=test_user.id  # <-- THIS FIXES THE NOT NULL CONSTRAINT
        )
        db_SQLAlchemy.session.add(test_game)
        db_SQLAlchemy.session.commit()
        
        # Keep track of the ID before exiting the app_context
        game_id = test_game.id

    # 2. Act: Send a POST request to delete that specific game ID
    response = admin_client.post(f"/games/{game_id}/delete", follow_redirects=True)
    
    # 3. Assert: Verify it's gone from the UI and the Database
    assert response.status_code == 200
    assert b"Temporary Game" not in response.data

    with app.app_context():
        deleted_game = db_SQLAlchemy.session.get(Game, game_id)
        assert deleted_game is None