import json
from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db

bp = Blueprint("tags", __name__, url_prefix="/tags")

@bp.route("/")
def index():
    db = get_db()
    
    _page = request.args.get('page')
    if (_page == None):
        currentPage = 1
    else:
        currentPage = int(_page)
    limit = 10
    offset = (currentPage - 1) * limit
    
    print('currentPage = ' + str(currentPage))
    print('offset = ' + str(offset))
    print('limit = ' + str(limit))
    
    """Show all the posts, most recent first."""
    tags = db.execute(
        "SELECT DISTINCT title"
        "  FROM tag t"
        " ORDER BY title ASC"
        " LIMIT " + str(offset) + "," + str(limit)
    ).fetchall()
    
    return render_template("tags/index.html", tags=tags, currentPage=currentPage)


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new tag."""
    if request.method == "POST":
        title = request.form["title"]
        comment = request.form["comment"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO tag (title, comment, author_id) VALUES (?, ?, ?)",
                (title, comment, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("tags.index"))
        
    return render_template("tags/create.html")