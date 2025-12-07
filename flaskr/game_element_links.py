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

bp = Blueprint("game_element_links", __name__, url_prefix="/game-element-links")

def get_game_element_links(ge_id):
    db = get_db()
    game_element_links = db.execute(
        "SELECT link, id as ge_link_id, game_element_id, title, comment, author_id, created"
        "  FROM game_element_link"
        " WHERE game_element_link.game_element_id = ?",
        (ge_id,),
    ).fetchall()

    if game_element_links is None:
        abort(404, f"There are no links for game element id {ge_id}.")

    return game_element_links 

@bp.route("/game-element-link/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new link for the current user."""
    if request.method == "POST":
        link = request.form["link"]
        game_element_id = request.form["game_element_id"]
        title = request.form["title"]
        comment = request.form.get("comment", "")
        
        print('link: ', link)
        print('game_element_id: ', game_element_id)
        print('title: ', title)
        print('comment: ', comment)
        
        error = None

        if not link:
            error = "link is required."
        if not game_element_id:
            error = "game_element_id is required."

        if error is not None:
            flash(error)
        else:
            
            print(g.user["id"])
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO game_element_link (link, author_id, game_element_id, title, comment) VALUES (?, ?, ?, ?, ?)",
                (link, g.user["id"], game_element_id, title, comment),
            )
            
            db.commit()
            return redirect(url_for('game_elements.update', ge_id=game_element_id))

    return render_template("game_elements/update.html")

@bp.route("/game-element-link/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM game_element_link WHERE id = ?", (id,))
        db.commit()
        
        game_element_id = request.form["game_element_id"]
        print(id)
        print(game_element_id)
        return redirect(url_for('game_elements.update', ge_id=game_element_id))
