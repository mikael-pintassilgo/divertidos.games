import os

from flask import Flask, app
from flask_talisman import Talisman
from flaskr.extensions import db_SQLAlchemy, login_manager

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Define a CSP that plays nice with Bootstrap 5
    csp = {
        'default-src': '\'self\'',
        'style-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',
            '\'unsafe-inline\''
        ],
        'script-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',
            'https://www.googletagmanager.com',
            'https://www.google-analytics.com',
            '\'unsafe-inline\'' 
        ],
        'img-src': [
            '\'self\'', 
            'data:', 
            'https://www.googletagmanager.com', 
            '*.google-analytics.com'  # Wildcard for images/pixels
        ],
        'connect-src': [
            '\'self\'', 
            '*.google-analytics.com',   # Wildcard fixes the "region1" issue
            'https://stats.g.doubleclick.net'
        ],
    }

    # Apply Talisman with the custom CSP
    Talisman(app, content_security_policy=csp)
    
    # SQLite configuration for SQLAlchemy
    db_path = os.path.join(app.instance_path, "flaskr.sqlite")
    
    login_manager.init_app(app)
    login_manager.login_view = 'login' # Куда редиректить неавторизованных
    
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY="dev",
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS = {"execution_options": {"sqlite_with_returning": False}}
    )

    #print("Testing mode: ", test_config)
    if test_config is None:
        #print("Loading instance config...")
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=False)
        # app.config.from_object(Config)
        SECRET_KEY = app.config['SECRET_KEY']
        if not SECRET_KEY:
            raise ValueError("No SECRET_KEY set for production environment")
        print(f"Secret Key is loaded and starts with: {SECRET_KEY[:2]}...")
    else:
        # load the test config if passed in
        app.config.update(test_config)
        print(test_config)
    
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register the database commands
    from . import db

    db.init_app(app)
    
    # Initialize SQLAlchemy
    db_SQLAlchemy.init_app(app)
    
    with app.app_context():
        db_SQLAlchemy.create_all() # Creates tables if they don't exist

    # apply the blueprints to the app
    from . import auth
    from . import profiles
    from . import home_page
    from . import blog
    from . import tags
    from . import quests
    from . import task
    from . import games
    from . import game_elements
    from . import game_element_tags
    from . import game_element_links
    from . import game_element_variants
    from . import services
    from . import contacts
    from . import votes
    from . import composition_of_elements
        
    app.register_blueprint(auth.bp)
    app.register_blueprint(profiles.bp)
    app.register_blueprint(home_page.bp)
    app.register_blueprint(blog.bp)
    app.register_blueprint(composition_of_elements.bp)
    app.register_blueprint(tags.bp)
    app.register_blueprint(quests.bp)
    app.register_blueprint(task.bp)
    app.register_blueprint(games.bp)
    app.register_blueprint(game_elements.bp)
    app.register_blueprint(game_element_tags.bp)
    app.register_blueprint(game_element_links.bp)
    app.register_blueprint(game_element_variants.bp)
    
    app.register_blueprint(services.bp)
    app.register_blueprint(contacts.bp)
    app.register_blueprint(votes.vote_api)

    # make url_for('index') == url_for('blog.index')
    # in another app, you might define a separate main index here with
    # app.route, while giving the blog blueprint a url_prefix, but for
    # the tutorial the blog will be the main index
    app.add_url_rule("/", endpoint="index")

    return app
