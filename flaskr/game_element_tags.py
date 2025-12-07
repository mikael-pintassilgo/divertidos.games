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

bp = Blueprint("game_element_tags", __name__, url_prefix="/game-element-tags")

def get_game_element_tags(ge_id):
    db = get_db()
    game_element_tags = db.execute(
        "SELECT game_element_tag.id as ge_tag_id, game_element_tag.game_element_id, game_element_tag.tag_id, game_element_tag.author_id, game_element_tag.created,"
        "       tag.title AS tag_title"
        "  FROM game_element_tag JOIN tag ON game_element_tag.tag_id = tag.id"
        " WHERE game_element_tag.game_element_id = ?",
        (ge_id,),
    ).fetchall()

    if game_element_tags is None:
        abort(404, f"There are no tags for game element id {ge_id}.")

    return game_element_tags 

@bp.route("/game-element-tag/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new tag for the current user."""
    if request.method == "POST":
        tag_id = request.form["tag_id"]
        game_element_id = request.form["game_element_id"]
        
        print('tag_id: ', tag_id)
        print('game_element_id: ', game_element_id)
        
        error = None

        if not tag_id:
            error = "tag_id is required."
        if not game_element_id:
            error = "game_element_id is required."

        if error is not None:
            flash(error)
        else:
            
            print(g.user["id"])
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO game_element_tag (tag_id, author_id, game_element_id) VALUES (?, ?, ?)",
                (tag_id, g.user["id"], game_element_id),
            )
            
            db.commit()
            return redirect(url_for('game_elements.update', ge_id=game_element_id))

    return render_template("game_elements/update.html")

@bp.route("/game-element-tag/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM game_element_tag WHERE id = ?", (id,))
        db.commit()
        
        game_element_id = request.form["game_element_id"]
        print(id)
        print(game_element_id)
        return redirect(url_for('game_elements.update', ge_id=game_element_id))
