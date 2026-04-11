from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required, role_required, user_has_role
from .db import get_db

bp = Blueprint("game_element_variants", __name__, url_prefix="/game-element-variants")

def get_game_element_variants(ge_id):
    db = get_db()
    user_id = g.user["id"] if g.user else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False
    
    game_element_variants = db.execute(
        "SELECT game_element_variant.id as ge_variant_id, "
        "       game_element_variant.game_element_id, "
        "       game_element_variant.title, "
        "       game_element_variant.author_id, "
        "       game_element_variant.created, "
        "       game_element_variant.status, "
        "       user.username AS author_name"
        "  FROM game_element_variant LEFT JOIN user ON game_element_variant.author_id = user.id"
        " WHERE game_element_variant.game_element_id = ?"
        "       AND (game_element_variant.status = 'public' OR ? OR game_element_variant.author_id = ?)",
        (ge_id, user_is_admin, user_id),
    ).fetchall()

    print('game_element_variants: ', game_element_variants)

    return game_element_variants 

@bp.route("/game-element-variant/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new variant for the current user."""
    if request.method == "POST":
        title = request.form["variant_title"]
        game_element_id = request.form["game_element_id"]
        game_id = request.form["game_id"]
        target_type = request.args.get('type') or 'game_and_element'
        
        print('game-element-variant/create called ')
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
        elif not game_id:
            error = "game_id is required."
            
        if error is not None:
            flash(error)
        else:
            
            print(g.user["id"])
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO game_element_variant (title, author_id, game_element_id, game_id, target_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                (title, g.user["id"], game_element_id, game_id, target_type, 'pending_review'),
            )
            
            db.commit()
            _url = url_for('game_elements.view', ge_id=game_element_id, game_id=game_id)
            print('redirecting to: ', _url)
            return redirect( _url )

    return render_template("game_elements/update.html")

@bp.route("/<int:id>/publish", methods=("GET", "POST"))
@login_required
@role_required("admin")
def publish(id):
    if request.method == "POST":
        game_element_id = id
        
        print('game-element-variant/publish called ')
        print('game_element_id: ', game_element_id)
        
        error = None

        if not game_element_id:
            error = "game element ID is required."
            
        if error is not None:
            flash(error)
        else:
            
            print('Publishing game element variant with ID: ', id)
            print(g.user["id"])
            
            db = get_db()
            db.execute(
                "UPDATE game_element_variant SET status = ? WHERE id = ?",
                ('public', id)
            )
            
            db.commit()

    _url = url_for('services.pending_reviews')
    return redirect( _url )
    
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
