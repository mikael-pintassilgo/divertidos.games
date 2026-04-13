from flask import Blueprint, jsonify
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.game_element_variants import get_game_element_variants

from .auth import login_required, role_required
from .db import get_db
from .game_element_tags import get_game_element_tags
from .game_element_links import get_game_element_links
from .blog import get_elements

bp = Blueprint("game_elements", __name__, url_prefix="/game_elements")


@bp.route("/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
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
        
        element_order = request.form["element_order"]
        print(f'element_order = {element_order}')
        
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
                    "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description, weight, previous_game_element_id, element_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, weight, previous_game_element_id, element_order),
                )
            else:
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, game_element_id, parent_element_id, author_id, game_id, description, weight, previous_game_element_id, element_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, weight, previous_game_element_id, element_order),
                )
            
            db.commit()
            if parent_element_id:
                game_title = request.args.get('title')
                parent = request.args.get('parent')
                return redirect(url_for("games.update", id=game_id, parent_id=parent_element_id, element_id=element_id))
            else:
                return redirect(url_for('games.update', id=game_id))

    game_id = request.args.get("game_id")
    
    print(f'game_id = {game_id}')
    
    return render_template("game_elements/create.html", game_id=game_id, 
                           parent_element_id=request.args.get("parent_element_id"),
                           currentPage=1)

@bp.route("/<int:ge_id>/delete", methods=("POST",))
@login_required
@role_required("admin")
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
@role_required("admin")
def update(ge_id):
    """Update an existing game element for the current user."""
    db = get_db()
    game_element = db.execute(
        """
        SELECT
            CASE WHEN type_of_id = 'element' THEN element_id
                 ELSE game_element_id
            END AS e_or_ge_id,
            *
        FROM game_and_element 
        WHERE id = ? AND author_id = ?
        """,
        (ge_id, g.user["id"]),
    ).fetchone()

    if game_element is None:
        abort(404)

    if request.method == "POST":
        print('--------------------------------------------------------')
        game_id = request.args.get("game_id")
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
        
        element_order = request.form["element_order"]
        print(f'element_order = {element_order}')
        
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
                    "weight = ?, link = ?, " \
                    "element_order = ? " \
                    "WHERE id = ?",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, previous_game_element_id, weight, link, element_order, ge_id),
                )
            else:
                db.execute(
                    "UPDATE game_and_element SET type_of_id = ?, game_element_id = ?, parent_element_id = ?, author_id = ?, " \
                    "game_id = ?, description = ?, previous_game_element_id = ?, weight = ?, link = ?, element_order = ? WHERE id = ?",
                    (type_of_id, element_id, parent_element_id, g.user["id"], game_id, description, previous_game_element_id, weight, link, element_order, ge_id),
                )

            db.commit()
            
            if parent_element_id:
                return redirect(url_for("games.update", id=game_id, parent_id=parent_element_id))
            else:
                return redirect(url_for('games.update', id=game_id))

    game_element_tags = get_game_element_tags(ge_id)
    game_element_links = get_game_element_links(ge_id)
    game_element_variants = get_game_element_variants(ge_id)
                
    game_id = request.args.get("game_id")
    print(f'2 game_id = {game_id}')
    print(f'ge_id = {ge_id}')
    return render_template("game_elements/update.html", 
                           ge_id=ge_id, 
                           game_element=game_element, 
                           game_id=game_id,
                           game_element_tags=game_element_tags,
                           game_element_links=game_element_links,
                           game_element_variants=game_element_variants)

def get_game_data(game_id):
    """Get game data by game id."""
    db = get_db()
    game_data = db.execute(
        """
        SELECT
            g.title as title
        FROM game g
        WHERE g.id = ?
        """,
        (game_id,),
    ).fetchone()
    return game_data

@bp.route("/<int:ge_id>/view", methods=("GET",))
def view(ge_id):
    """View an existing game element for the current user."""
    db = get_db()
    game_element = db.execute(
        """
        SELECT
            CASE WHEN type_of_id = 'element' THEN element_id
                 ELSE game_element_id
            END AS e_or_ge_id,
            element.title as element_title,
            game_and_element.*
        FROM game_and_element LEFT JOIN element ON game_and_element.element_id = element.id
        WHERE game_and_element.id = ?
        """,
        (ge_id,),
    ).fetchone()

    if game_element is None:
        abort(404)

    game_element_tags = get_game_element_tags(ge_id)
    game_element_links = get_game_element_links(ge_id)
    game_element_variants = get_game_element_variants(ge_id)
                
    for key, value in request.args.items():
        print(f'{key}: {value}')
    
    game_id = request.args.get("game_id")
    game_data = get_game_data(game_id)
    
    print(f'2 game_id = {game_id}')
    print(f'ge_id = {ge_id}')
    print('Tags: ', game_element_tags)
    print('Variants: ', game_element_variants)
    
    return render_template("game_elements/view.html", 
                           ge_id=ge_id, 
                           game_element=game_element, 
                           game_id=game_id,
                           game_title=game_data['title'],
                           game_element_tags=game_element_tags,
                           game_element_links=game_element_links,
                           game_element_variants=game_element_variants)

# Services
@bp.route("/load-parent-composition", methods=("GET", "POST"))
@login_required
@role_required("admin")
def load_parent_composition():
    game_id = request.args.get("game_id")
    parent_game_element_id = request.args.get("parent_game_element_id")
    parent_element_id = request.args.get("element_id")
    
    db = get_db()
    elements = db.execute(
        "SELECT DISTINCT e.* FROM element e"
        "  JOIN composition_of_element c ON e.id = c.subelement_id"
        " WHERE c.element_id = ?",
        (parent_element_id,)
    ).fetchall()

    for element in elements:
        db.execute(
            "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, NULL)",
            ('element', element['id'], parent_game_element_id, g.user["id"], game_id, ""),
        )

    db.commit()

    return redirect(url_for("games.update", id=game_id, parent_id=parent_game_element_id, element_id=parent_element_id))