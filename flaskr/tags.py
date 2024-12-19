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
        "  FROM element_tag et"
        " ORDER BY title ASC"
        " LIMIT " + str(offset) + "," + str(limit)
    ).fetchall()
    
    return render_template("tags/index.html", tags=tags, currentPage=currentPage)
