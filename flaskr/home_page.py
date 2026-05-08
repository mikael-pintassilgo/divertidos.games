from flask import Blueprint
from flask import g
from flask import render_template
from flask import request
from flask_login import current_user

from .db import get_db

bp = Blueprint("home_page", __name__)

@bp.route("/")
def index():
    print("Rendering home page")
    print(f"Index access - User: {current_user}, Auth: {current_user.is_authenticated}")
    print(f"User roles: {[role.name for role in current_user.roles]}") if current_user.is_authenticated else print("No user logged in")
    return render_template("home_page.html")
