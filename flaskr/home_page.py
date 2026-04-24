from flask import Blueprint
from flask import g
from flask import render_template
from flask import request

from .db import get_db

bp = Blueprint("home_page", __name__)

@bp.route("/")
def index():
    print("Rendering home page")
    return render_template("home_page.html")
