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

bp = Blueprint("games", __name__, url_prefix="/games")

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
    
    """Show all the games, most recent first."""
    games = db.execute(
        "SELECT g.id, title, body, created, author_id, username, comment"
        "  FROM game g JOIN user u ON g.author_id = u.id"
        " ORDER BY created DESC"
        " LIMIT " + str(offset) + "," + str(limit)
    ).fetchall()
    
    return render_template("games/index.html", games=games, tag="", currentPage=currentPage)


def get_game(id, check_author=True):
    """Get a game and its author by id.

    Checks that the id exists and optionally that the current user is
    the author.

    :param id: id of game to get
    :param check_author: require the current user to be the author
    :return: the game with author information
    :raise 404: if a game with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    db = get_db()

    game = (
        db
        .execute(
            "SELECT g.id, title, body, comment, created, author_id, username"
            "  FROM game g JOIN user u ON g.author_id = u.id"
            " WHERE g.id = ?",
            (id,),
        )
        .fetchone()
    )
    tags = (
        db
        .execute(
            "SELECT t.id, title, comment"
            "  FROM game_tag t JOIN user u ON t.author_id = u.id"
            " WHERE t.game_id = ?"
            " ORDER BY created ASC",
            (id,),
        ).fetchall()
    )
    links = (
        db
        .execute(
            "SELECT l.id, title, comment"
            "  FROM game_link l JOIN user u ON l.author_id = u.id"
            " WHERE l.game_id = ?"
            " ORDER BY created ASC",
            (id,),
        ).fetchall()
    )
    elements = (
        db
        .execute(
            "SELECT e.id, e.title, e.body, e.created, e.tags"
            "  FROM element e JOIN user u ON e.author_id = u.id"
            " INNER JOIN game_and_element ge ON e.id = ge.element_id"
            " WHERE ge.game_id = ?",
            (id,),
        ).fetchall()
    )

    if game is None:
        abort(404, f"Game id {id} doesn't exist.")

    game_data = {
        "game": game,
        "tags": tags,
        "links": links,
        "elements": elements,
    }
    return game_data


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new game for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        comment = request.form["comment"]
        tags = "" #request.form["tags"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO game (title, body, author_id, comment) VALUES (?, ?, ?, ?)",
                (title, body, g.user["id"], comment),
            )
            db.commit()
            return redirect(url_for("games.index"))

    return render_template("games/create.html")


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    game_data = get_game(id)

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        comment = request.form["comment"]
        
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE game SET title = ?, body = ?, comment = ?, WHERE id = ?", (title, body, comment, id)
            )
            db.commit()
            return redirect(url_for("games.index"))

    return render_template("games/update.html", game=game_data["game"], tags=game_data["tags"], links=game_data["links"])

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a game if the current user is the author."""
    game_data = get_game(id)
    return render_template("games/view.html",
                           game=game_data["game"], 
                           elements=game_data["elements"], 
                           tags=game_data["tags"], 
                           links=game_data["links"])
