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

def get_task(id):
    """Get a post and its author by id.

    Checks that the id exists.

    :param id: id of post to get
    :return: the quest with tasks
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    db = get_db()

    task_and_quest_info = (
        db
        .execute(
            "SELECT t.id, t.description, t.image_static_link, t.next_task_id, "
            "       t.first_clue, t.second_clue, t.third_clue, t.answer,"
            "       q.title q_title"
            "  FROM quest_task t"
            " INNER JOIN quest q"
            "       ON q.id = t.quest_id"
            " WHERE t.id = ?",
            (id,),
        )
        .fetchone()
    )
    if task_and_quest_info is None:
        abort(404, f"Task id {id} doesn't exist.")

    return task_and_quest_info

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a task."""
    task_and_quest_info = get_task(id)
    return render_template("quests/task/view.html", task=task_and_quest_info)
