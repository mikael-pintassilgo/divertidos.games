from flask import Blueprint
from flask import g
from flask import render_template
from flask import request

from .db import get_db

bp = Blueprint("contacts", __name__, url_prefix="/contacts")

@bp.route("/")
def index():
    return render_template("contacts.html")

    """View a list of authors."""
    db = get_db()
    authors = db.execute(
        "SELECT username"
        "  FROM user",
    ).fetchall()
    
    for val in authors:
        print(val["username"])

    return render_template('blog/authors.html', authors=authors)