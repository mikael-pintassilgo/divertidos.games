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

bp = Blueprint("game_element_variants", __name__, url_prefix="/game-element-variants")

def get_game_element_variants(ge_id):
    db = get_db()
    game_element_variants = db.execute(
        "SELECT game_element_variant.id as ge_variant_id, game_element_variant.game_element_id, game_element_variant.title, game_element_variant.author_id, game_element_variant.created,"
        "       user.username AS author_name"
        "  FROM game_element_variant JOIN user ON game_element_variant.author_id = user.id"
        " WHERE game_element_variant.game_element_id = ?",
        (ge_id,),
    ).fetchall()

    if game_element_variants is None:
        abort(404, f"There are no variants for game element id {ge_id}.")

    print('game_element_variants: ', game_element_variants)

    return game_element_variants 

@bp.route("/game-element-variant/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new variant for the current user."""
    if request.method == "POST":
        title = request.form["variant_title"]
        game_element_id = request.form["game_element_id"]
        target_type = request.args.get('type') or 'game_and_element'
        
        print('title: ', title)
        print('game_element_id: ', game_element_id)
        print('target_type: ', target_type)
        
        error = None

        if not title:
            error = "title is required."
        if not game_element_id:
            error = "game_element_id is required."

        if target_type not in ['game_and_element', 'element']:
            error = "Invalid target type."
        elif target_type == 'game_and_element':
            game_id = None
        elif target_type == 'game':
            game_id = request.form["game_id"]
            if not game_id:
                error = "game_id is required for game target type."
            
        if error is not None:
            flash(error)
        else:
            
            print(g.user["id"])
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO game_element_variant (title, author_id, game_element_id, game_id, target_type) VALUES (?, ?, ?, ?, ?)",
                (title, g.user["id"], game_element_id, game_id, target_type),
            )
            
            db.commit()
            return redirect(url_for('game_elements.update', ge_id=game_element_id))

    return render_template("game_elements/update.html")

@bp.route("/game-element-variant/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM game_element_variant WHERE id = ?", (id,))
        db.commit()
        
        game_element_id = request.form["game_element_id"]
        print(id)
        print(game_element_id)
        return redirect(url_for('game_elements.update', ge_id=game_element_id))
