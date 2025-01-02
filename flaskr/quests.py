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

bp = Blueprint("quests", __name__, url_prefix="/quests")

@bp.route("/")
def index():
    db = get_db()
    """
    barreiro_quests = [{
        'city': 'Barreiro',
        'title': 'Old City',
        'description': 'A walk through the historic part of Barreiro. \nInteresting facts about the city and its inhabitants.',
        'static_link': url_for('static', filename='quests/Barreiro/old-city.html'),
        'price': 'free',
        'start_point': 'Terminal',
    }]"""
    
    """Show all the posts, most recent first."""
    barreiro_quests = db.execute(
        "SELECT *"
        "  FROM quest"
        " WHERE city = 'City'"
    ).fetchall()
    
    quests = {
        'barreiro_quests': barreiro_quests,
    }
    
    print(quests)    
    return render_template("quests/index.html", quests=quests)

@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new quest for the current user."""
    if request.method == "POST":
        error = ''

        city = request.form["city"]
        title = request.form["title"]
        description = request.form["description"]
        price = request.form["price"]
        start_point = request.form["start_point"]
        static_link = request.form["static_link"]
        image_static_link = request.form["image_static_link"]
        first_task_id = request.form["first_task_id"]
        
        if not city:
            error += "City is required.\n"
        if not title:
            error += "Title is required.\n"
        #if not static_link:
        #    error += "Static link is required.\n"
        if not start_point:
            error += "Start point is required.\n"
        
        if error != '':
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO quest (author_id, city, title, description, price, start_point, static_link, image_static_link, first_task_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (g.user["id"], city, title, description, price, start_point, static_link, image_static_link, first_task_id),
            )
            db.commit()
            return redirect(url_for("quests.index"))

    return render_template("quests/create.html")


def get_quest(id):
    """Get a post and its author by id.

    Checks that the id exists.

    :param id: id of post to get
    :return: the quest with tasks
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    db = get_db()

    quest = (
        db
        .execute(
            "SELECT q.id, q.title, q.description, q.city, q.price,"
            "       q.image_static_link, q.static_link, q.start_point, q.first_task_id"
            "  FROM quest q"
            " WHERE q.id = ?",
            (id,),
        )
        .fetchone()
    )
    tasks = (
        db
        .execute(
            "SELECT id, description"
            "  FROM quest_task"
            " WHERE quest_id = ?"
            " ORDER BY created ASC",
            (id,),
        ).fetchall()
    )

    if quest is None:
        abort(404, f"Quest id {id} doesn't exist.")

    quest_data = {
        "quest": quest,
        "tasks": tasks,
    }
    return quest_data

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a quest."""
    quest_data = get_quest(id)
    return render_template("quests/view.html", quest=quest_data["quest"], tasks=quest_data["tasks"])
