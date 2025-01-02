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

bp = Blueprint("task", __name__, url_prefix="/task")

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a task."""
    return render_template("quests/task/view.html")
