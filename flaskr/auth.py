import functools
from urllib.parse import urljoin, urlparse
from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from flask_login import login_user, logout_user
from flask_login import current_user
from flask_login import login_required

from sqlalchemy import select
from flaskr.models import User, Role  # Import your SQLAlchemy models
from flaskr.extensions import db_SQLAlchemy, login_manager

bp = Blueprint("auth", __name__, url_prefix="/auth")

# --- Helper Functions (SQLAlchemy 2.0 Style) ---

@login_manager.user_loader
def load_user(user_id):
    user = db_SQLAlchemy.session.get(User, int(user_id))
    print(f"Loading user with ID: {user_id}, Found: {user.username if user else 'None'}")
    print(f"User: {user}")
    return user

def user_has_role(user_id, role_name):
    user = db_SQLAlchemy.session.get(User, user_id)
    if user:
        return any(role.name == role_name for role in user.roles)
    return False

def get_user_roles(user_id):
    user = db_SQLAlchemy.session.get(User, user_id)
    return [role.name for role in user.roles] if user else []

# --- Decorators ---
def role_required(role_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # current_user.is_authenticated checks if the user is logged in
            if not current_user.is_authenticated or \
               not any(role.name == role_name for role in current_user.roles):
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# --- Routes ---

@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."

        if error is None:
            # Check if user exists
            existing_user = db_SQLAlchemy.session.execute(select(User).where(User.username == username)).scalar()
            if existing_user:
                error = f"User {username} is already registered."
            else:
                # 1. Create User
                new_user = User(username=username, password=generate_password_hash(password))
                
                # 2. Assign default 'user' role
                default_role = db_SQLAlchemy.session.execute(select(Role).where(Role.name == 'user')).scalar()
                if default_role:
                    new_user.roles.append(default_role)
                
                db_SQLAlchemy.session.add(new_user)
                db_SQLAlchemy.session.commit()
                
                login_user(new_user)
                return redirect(after_login(new_user.id))

        flash(error)
    return render_template("auth/register.html")

@bp.route("/login", methods=("GET", "POST"))
def login():
    print("Login route accessed")
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        print(f"Attempting login for username: {username}")
        
        user = db_SQLAlchemy.session.execute(select(User).where(User.username == username)).scalar()
        print(f"User found: {user.username if user else 'None'}")
        
        if user is None or not check_password_hash(user.password, password):
            flash("Incorrect username or password.")
        else:
            login_user(user) # Flask-Login takes over here
            
            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                next_page = url_for('index')
            return redirect(next_page)
        
    return render_template("auth/login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@bp.route("/admin/assign-role", methods=["POST"])
@role_required("admin")
def assign_role():
    user_id = request.form["user_id"]
    role_name = request.form["role"]

    user = db_SQLAlchemy.session.get(User, user_id)
    role = db_SQLAlchemy.session.execute(select(Role).where(Role.name == role_name)).scalar()

    if user and role and role not in user.roles:
        user.roles.append(role)
        db_SQLAlchemy.session.commit()
        return "Role assigned successfully"
    return "Error: User or Role not found", 400

# --- Utility ---

def after_login(user_id):
    #session["user_id"] = user_id
    #session["roles"] = get_user_roles(user_id)
    
    next_page = request.form.get('next') or request.args.get('next')
    if not next_page or not is_safe_url(next_page):
        next_page = url_for('index')
    return next_page

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
