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

bp = Blueprint("game_elements", __name__, url_prefix="/game_elements")


# Game Elements
@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    print('------------------ CREATE GAME ELEMENT -------------------')
    print(request.method)
    
    """Create a new game element for the current user."""
    if request.method == "POST":
        print('--------------------------------------------------------')
        
        game_id = request.form["game_id"]
        print(f'game_id = {game_id}')
        
        type_of_id = request.form["type_of_id"]
        print(f'type_of_id = {type_of_id}')
        
        element_id = request.form["element_id"]
        print(f'element_id = {element_id}')
        
        parent_element_id = request.form["parent_element_id"]
        print(f'parent_element_id = {parent_element_id}')
        
        description = request.form["description"]
        print(f'description = {description}')
        
        weight = request.form["ge_weight"]
        print(f'weight = {weight}')
        
        previous_game_element_id = request.form["previous_ge_id"]
        print(f'previous_game_element_id = {previous_game_element_id}')
        print('--------------------------------------------------------')
        
        error = None

        if not element_id:
            error = "Element ID is required."

        if error is not None:
            flash(error)
        else:
            print(type_of_id)
            print(element_id)
            print(g.user["id"])
            print((game_id))
            
            db = get_db()
            if (type_of_id == 'element'):
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description, weight, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, weight, previous_game_element_id),
                )
            else:
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, game_element_id, parent_element_id, author_id, game_id, description, weight, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, weight, previous_game_element_id),
                )
            
            db.commit()
            if parent_element_id:
                game_title = request.args.get('title')
                parent = request.args.get('parent')
                return redirect(url_for("games.update_game_elements_of_the_parent", game_id=game_id, parent_id=parent_element_id)+"?title="+game_title+"&parent="+parent)
            else:
                return redirect(url_for('games.update', id=game_id))

    game_id = request.args.get("game_id")
    print(f'game_id = {game_id}')
    return render_template("game_elements/create.html", game_id=game_id)

@bp.route("/<int:ge_id>/delete", methods=("POST",))
@login_required
def delete(ge_id):
    """Delete a game element.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    #print('ge_id = ', ge_id)
    #print('game_id = ', game_id)
    game_id = request.form["game_id"]
    print(f'game_id = {game_id}')
    
    db = get_db()
    db.execute("DELETE FROM game_and_element WHERE id = ?", (ge_id,))
    db.commit()
    
    try:
        parent_id = request.args.get('parent_id')
    except:
        parent_id = None
       
    if parent_id:
        game_title = request.args.get('title')
        parent = request.args.get('parent')
        
        print(f"parent_id = {parent_id}")
        
        return redirect(url_for("games.update_game_elements_of_the_parent", game_id=game_id, parent_id=parent_id)+"?title="+game_title+"&parent="+parent)
    else:
        return redirect(url_for('games.update', id=game_id))   

@bp.route("/<int:ge_id>/update", methods=("GET", "POST"))
@login_required
def update(ge_id):
    """Update an existing game element for the current user."""
    db = get_db()
    game_element = db.execute(
        "SELECT * FROM game_and_element WHERE id = ? AND author_id = ?",
        (ge_id, g.user["id"]),
    ).fetchone()

    if game_element is None:
        abort(404)

    if request.method == "POST":
        print('--------------------------------------------------------')
        game_id = request.form["game_id"]
        print(f'1 game_id = {game_id}')

        type_of_id = request.form["type_of_id"]
        print(f'type_of_id = {type_of_id}')
        
        element_id = request.form["element_id"]
        print(f'element_id = {element_id}')
        
        parent_element_id = request.form["parent_element_id"]
        print(f'parent_element_id = {parent_element_id}')
        
        description = request.form["description"]
        print(f'description = {description}')
        
        previous_game_element_id = request.form["previous_ge_id"]
        print(f'previous_game_element_id = {previous_game_element_id}')
        
        link = request.form["ge_link"]
        print(f'link = {link}')
        
        weight = request.form["ge_weight"]
        print(f'weight = {weight}')
        
        print('--------------------------------------------------------')
        
        error = None

        if not element_id:
            error = "Element ID is required."

        if error is not None:
            flash(error)
        else:
            print(type_of_id)
            print(element_id)
            print(g.user["id"])
            print((game_id))
            
            db = get_db()
            if (type_of_id == 'element'):
                db.execute(
                    "UPDATE game_and_element SET type_of_id = ?, element_id = ?,"\
                    "parent_element_id = ?, author_id = ?, game_id = ?, description = ?, previous_game_element_id = ?, " \
                    "weight = ?, link = ? " \
                    "WHERE id = ?",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, previous_game_element_id, weight, link, ge_id),
                )
            else:
                db.execute(
                    "UPDATE game_and_element SET type_of_id = ?, game_element_id = ?, parent_element_id = ?, author_id = ?, " \
                    "game_id = ?, description = ?, previous_game_element_id = ?, weight = ?, link = ? WHERE id = ?",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, previous_game_element_id, weight, link, ge_id),
                )

            db.commit()
            if parent_element_id:
                game_title = request.args.get('title')
                parent = request.args.get('parent')
                return redirect(url_for("games.update_game_elements_of_the_parent", game_id=game_id, parent_id=parent_element_id)+"?title="+game_title+"&parent="+parent)
            else:
                return redirect(url_for('game_elements.update', ge_id=ge_id))

    game_id = request.args.get("game_id")
    print(f'2 game_id = {game_id}')
    print(f'ge_id = {ge_id}')
    return render_template("game_elements/update.html", ge_id=ge_id, game_element=game_element, game_id=game_id)
# End Game Elements