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
from .blog import get_element_by_title

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
    game_elements = (
        db
        .execute(
            "SELECT 0 AS consist_count,"
            "       e.id AS e_id, "
            "       e.title, "
            "       e.body, "
            "       e.created, "
            "       e.tags, "
            "       ge.type_of_id,  "
            "       ge.previous_game_element_id AS previous_ge_id,  "
            "       previous_ge.description AS previous_ge_description,  "
            "       ge.id AS ge_id,  "
            "       ge.description,  "
            "       ge.link,  "
            "       ge.weight,  "
            "       ge.parent_element_id AS parent_element_id"
            "  FROM game_and_element AS ge"
            " INNER JOIN element AS e "
            "    ON e.id = ge.element_id AND ge.type_of_id = 'element' "
            "  LEFT JOIN game_and_element AS previous_ge "
            "    ON ge.previous_game_element_id = previous_ge.id"
            " WHERE ge.game_id = ?"
            " UNION ALL "
            "SELECT 0 AS consist_count,"
            "       'e.id',  "
            "       'e.title',  "
            "       'ge.body',  "
            "       'ge.created',  "
            "       'ge.tags', "
            "       ge.type_of_id,  "
            "       ge.previous_game_element_id,  "
            "       previous_ge.description AS previous_ge_description,  "
            "       ge.id,  "
            "       ge.description,  "
            "       ge.link,  "
            "       ge.weight,  "
            "       ge.parent_element_id"
            "  FROM game_and_element AS ge"
            "  LEFT JOIN game_and_element AS previous_ge "
            "    ON ge.previous_game_element_id = previous_ge.id"
            " WHERE ge.type_of_id = 'game_element' AND ge.game_id = ?",
            (id,id,),
        ).fetchall()
    )
    game_elements_hierarchy = (
        db
        .execute(
            "SELECT ge.id as ge_id, COUNT(ge2.id) as consist_count"
            "  FROM game_and_element ge"
            " INNER JOIN game_and_element ge2 ON ge2.parent_element_id = ge.id"
            " WHERE ge.game_id = ?"
            " GROUP BY ge.id",
            (id,),
        ).fetchall()
    )

    # Check if game exists before processing
    if game is None:
        abort(404, f"Game id {id} doesn't exist.")

    # Build a tree structure for game_elements
    def build_element_tree(elements, parent_id=None):
        tree = []
        for element in elements:
            if (element['parent_element_id'] == parent_id or 
                (element['parent_element_id'] is None and parent_id is None) or
                (element['parent_element_id'] == '' and parent_id is None)):
                print("Building tree for element: ", element['title'])
                children = build_element_tree(elements, element['ge_id'])
                element['children'] = children
                tree.append(element)
        return tree

    game_elements_tree = build_element_tree([dict(element) for element in game_elements])
    print("game_elements_tree = ", game_elements_tree)

    # Map consist_count from game_elements_hierarchy to game_elements by ge_id
    consist_count_map = {row['ge_id']: row['consist_count'] for row in game_elements_hierarchy}
    # Convert sqlite3.Row to dict and add consist_count
    game_elements = [
        dict(element, consist_count=consist_count_map.get(element['ge_id'], 0))
        for element in game_elements
    ]
    #print("game_elements = ", game_elements)
    #print("element id = " + str(game_elements[0]['e_id']))
    
    if game is None:
        abort(404, f"Game id {id} doesn't exist.")

    game_data = {
        "game": game,
        "tags": tags,
        "links": links,
        "game_elements": game_elements,
        "game_elements_hierarchy": game_elements_hierarchy,
        "game_elements_tree": game_elements_tree,
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

# Recursively insert game elements
def insert_elements(not_existed_items, db, game_id, data, parent_ge_id=None):
        
    def insert_simple_value(key, value, _parent_ge_id=parent_ge_id):
        # Try to find element by title
        row = get_element_by_title(db, key)
        if row is None:
            # element not found: skip inserting into game_and_element
            not_existed_items.append(key)
            return None
        element_id = row["id"]
        
        cursor = db.execute(
            "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description) VALUES (?, ?, ?, ?, ?, ?)",
            ("element", element_id, _parent_ge_id, g.user["id"], game_id, str(value)),
        )
        current_ge_id = cursor.lastrowid
        return current_ge_id
        
    def insert_dict(key, value, p_parent_ge_id):
        current_ge_id = insert_simple_value(key, '', p_parent_ge_id) # Create a parent game_element for the dict
        
        if current_ge_id is None:
            return None

        # Recursively insert nested elements
        dict_description = insert_elements(not_existed_items,db, game_id, value, current_ge_id)
        if dict_description:
            db.execute(
                "UPDATE game_and_element SET description = ? WHERE id = ?",
                (dict_description.strip(), current_ge_id),
            )
    
    simple_values_as_one_string = ''
    only_simiple_values = True
    for key, value in data.items():
        if key in ["title"]:
            continue
        
        if isinstance(value, dict):
            insert_dict(key, value, parent_ge_id)
            only_simiple_values = False
            
        elif isinstance(value, list):
            only_simiple_values = False
            current_ge_id = insert_simple_value(key, '') # Create a parent game_element for the list
            if current_ge_id is None:
                continue
            
            # Create game_element for list items
            list_description = ""
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    insert_dict(key, item, current_ge_id)
                else:
                    insert_simple_value(key, item, current_ge_id)
                    if list_description:
                        list_description += f" - {str(item).strip()}\n"
                    else:
                        list_description = str(item)
                    
            # Update the parent game_element description with the list items
            if list_description:
                db.execute(
                    "UPDATE game_and_element SET description = ? WHERE id = ?",
                    (list_description.strip(), current_ge_id),
                )
        else:
            if simple_values_as_one_string:
                simple_values_as_one_string += f" - {str(value).strip()}"
            else:
                simple_values_as_one_string = str(value).strip()
            insert_simple_value(key, value)
            
    if only_simiple_values:
        return simple_values_as_one_string
    else:
        return ''

def import_game_data(game_data_json, is_checking=False):
    """Import a new game for the current user."""
    db = get_db()
    
    game_info = game_data_json.get("game", {})
    title = game_info.get("title", "")
    
    if not title:
        abort(400, "Game title is required.")
    
    # Insert main game
    cursor = db.execute(
        "INSERT INTO game (title, body, author_id, comment) VALUES (?, ?, ?, ?)",
        (title, "", g.user["id"], ""),
    )
    game_id = cursor.lastrowid

    not_existed_items = []
    insert_elements(not_existed_items, db, game_id, game_info)
    db.commit()
    return game_id, not_existed_items

@bp.route("/import-game", methods=("GET", "POST"))
@login_required
def import_game():
    """Import a new game for the current user."""
    if request.method == "POST":
        game_json = request.form["json_input"]
        error = None

        if not game_json:
            error = "Game JSON is required."

        if error is not None:
            flash(error)
        else:
            game_data_json = json.loads(game_json)
            game_id, not_existed_items = import_game_data(game_data_json)
            print("not_existed_items: ", not_existed_items)
            return redirect(url_for("games.view", id=game_id))

    return render_template("games/import_game.html")

def get_only_game_elements_of_the_parent(game_elements, parent_element_id):
    if parent_element_id == None:
        return [element for element in game_elements if element["parent_element_id"]\
            is None or element["parent_element_id"] == '']
    else:
        return [element for element in game_elements if element["parent_element_id"] == parent_element_id]

def handle_sub_elements(game_elements, parent_element_id, full_description, level):
    sub_elements = get_only_game_elements_of_the_parent(game_elements, parent_element_id)
    if sub_elements:
        for element in sub_elements:
            indent = '    ' * level
            if element['type_of_id'] == 'element':
                full_description += f"{indent}{element['title']}\n{indent}{element['description']}\n\n"
            else:
                full_description += f"{indent}{element['description']}\n\n"
            full_description = handle_sub_elements(game_elements, element['ge_id'], full_description, level + 1)
    return full_description

@bp.route("/<int:id>/get_full_description", methods=("GET", "POST"))
def get_full_description(id):
    game_data = get_game(id)
    
    full_description = ''
    full_description = handle_sub_elements(game_data['game_elements'], None, full_description, 0)

    return render_template("games/full_description.html",
                           game=game_data["game"],
                           full_description=full_description,)

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    game_data = get_game(id)
    parent_id = request.args.get('parent_id')
    print(f"229 parent_id = {parent_id}")
    if parent_id:
        game_elements_data = get_game_elements_of_the_parent(id, parent_id)
        game_elements_parents = game_elements_data["game_elements_parents"]
        game_elements = game_elements_data["game_elements"]
        print("229 game_elements_data = ", game_elements_data)
    else:
        game_elements = game_data["game_elements"]
        game_elements_parents = []

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
                "UPDATE game SET title = ?, body = ?, comment = ?"
                "WHERE id = ?",
                (title, body, comment, id)
            )
            db.commit()
            return redirect(url_for("games.index"))

    return render_template("games/update.html",
                           game=game_data["game"],
                           tags=game_data["tags"],
                           links=game_data["links"],
                           game_elements=game_elements,
                           game_elements_parents=game_elements_parents,
                           parent_id=parent_id)

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a game if the current user is the author."""
    print('Viewing game id = ', id)
    game_data = get_game(id)
    parent_id = request.args.get('parent_id')
    print(f"230 parent_id = {parent_id}")
    if parent_id:
        game_elements_data = get_game_elements_of_the_parent(id, parent_id)
        game_elements_parents = game_elements_data["game_elements_parents"]
        game_elements = game_elements_data["game_elements"]
        print("229 game_elements_data = ", game_elements_data)
    else:
        game_elements = game_data["game_elements"]
        game_elements_parents = []
    
    return render_template("games/view.html",
                           game=game_data["game"], 
                           game_elements=game_elements,
                           game_elements_parents=game_elements_parents,
                           parent_id=parent_id,
                           tags=game_data["tags"], 
                           links=game_data["links"],
                           game_elements_hierarchy=game_data["game_elements_hierarchy"],
                           game_elements_tree=game_data["game_elements_tree"],)

def get_sql_for_elements_of_the_parent():
    return ("SELECT 0 AS consist_count,"
            "       e.id AS e_id, "
            "       e.title, "
            "       e.body, "
            "       e.created, "
            "       e.tags, "
            "       ge.type_of_id,  "
            "       ge.previous_game_element_id AS previous_ge_id,  "
            "       previous_ge.description AS previous_ge_description,  "
            "       ge.id AS ge_id,  "
            "       ge.description,  "
            "       ge.link,  "
            "       ge.weight,  "
            "       ge.parent_element_id AS parent_element_id"
            "  FROM game_and_element AS ge"
            " INNER JOIN element AS e "
            "    ON e.id = ge.element_id AND ge.type_of_id = 'element' "
            "  LEFT JOIN game_and_element AS previous_ge "
            "    ON ge.previous_game_element_id = previous_ge.id"
            " WHERE ge.game_id = ? AND ge.parent_element_id = ?"
            " UNION ALL "
            "SELECT 0 AS consist_count,"
            "       'e.id',  "
            "       'e.title',  "
            "       'ge.body',  "
            "       'ge.created',  "
            "       'ge.tags', "
            "       ge.type_of_id,  "
            "       ge.previous_game_element_id,  "
            "       previous_ge.description AS previous_ge_description,  "
            "       ge.id,  "
            "       ge.description,  "
            "       ge.link,  "
            "       ge.weight,  "
            "       ge.parent_element_id"
            "  FROM game_and_element AS ge"
            "  LEFT JOIN game_and_element AS previous_ge "
            "    ON ge.previous_game_element_id = previous_ge.id"
            " WHERE ge.type_of_id = 'game_element' AND ge.game_id = ? AND ge.parent_element_id = ?"
    )
    
def get_game_elements_of_the_parent(game_id, parent_element_id):
    db = get_db()

    game_elements = (
        db
        .execute(
            get_sql_for_elements_of_the_parent(),
            (game_id, int(parent_element_id), game_id, int(parent_element_id),),
        ).fetchall()
    )
    game_elements_hierarchy = (
        db
        .execute(
            "SELECT ge.id as ge_id, COUNT(ge2.id) as consist_count"
            "  FROM game_and_element ge"
            " INNER JOIN game_and_element ge2 ON ge2.parent_element_id = ge.id"
            " WHERE ge.game_id = ? AND ge.parent_element_id = ?"
            " GROUP BY ge.id",
            (game_id, parent_element_id,),
        ).fetchall()
    )
    
    # Get all parents of the game element with id = parent_element_id
    def get_parents(db, ge_id):
        parents = []
        current_id = ge_id
        while current_id:
            parent = db.execute(
                """
                SELECT gae.id, gae.description, gae.parent_element_id, gae.type_of_id,
                       CASE
                           WHEN gae.description IS NOT NULL AND gae.description != '' THEN gae.description
                           WHEN gae.type_of_id = 'element' THEN e.title
                           WHEN gae.type_of_id = 'game_element' THEN ge2.description
                           ELSE gae.description
                       END AS parent_title,
                       e.title AS element_title,
                       ge2.description AS game_element_title
                  FROM game_and_element gae
                  LEFT JOIN element e
                    ON gae.type_of_id = 'element' AND gae.element_id = e.id
                  LEFT JOIN game_and_element ge2
                    ON gae.type_of_id = 'game_element' AND gae.game_element_id = ge2.id
                 WHERE gae.id = ?
                """,
                (current_id,)
            ).fetchone()
            
            if parent:
                parents.insert(0, {"id": current_id, "description": parent["parent_title"], "element_title": parent["element_title"], "game_element_title": parent["game_element_title"]})
                current_id = parent["parent_element_id"]
            else:
                break
        return parents

    game_elements_parents = get_parents(db, parent_element_id)
    print("All parents of element id", parent_element_id, ":", game_elements_parents)
    for idx, parent in enumerate(game_elements_parents):
        print(f"Parent {idx}:")
        for key, value in parent.items():
            print(f"  {key}: {value}")

    # Map consist_count from game_elements_hierarchy to game_elements by ge_id
    consist_count_map = {row['ge_id']: row['consist_count'] for row in game_elements_hierarchy}
    # Convert sqlite3.Row to dict and add consist_count
    game_elements = [
        dict(element, consist_count=consist_count_map.get(element['ge_id'], 0))
        for element in game_elements
    ]
    print("game_elements = ", game_elements)
    #print("element id = " + str(game_elements[0]['e_id']))
    
    game_data = {
        "game_elements": game_elements,
        "game_elements_hierarchy": game_elements_hierarchy,
        "game_elements_parents": game_elements_parents,
    }
    return game_data

@bp.route("/<int:game_id>/view/game-elements/<int:parent_id>", methods=("GET",))
def view_game_elements_of_the_parent(game_id, parent_id):
    game_title = request.args.get('title')
    parent = request.args.get('parent')
    print('--------------------------------------------------------')
    print(f"game_title: {game_title}")
    print(f"game_id: {game_id}")
    print(f"parent_id: {parent_id}")
    
    game_elements_data = get_game_elements_of_the_parent(game_id, parent_id)
    #game_elements = get_game(game_id)
    return render_template("games/view_ge_of_the_parent.html",
                           game_elements=game_elements_data["game_elements"],
                           game_title=game_title,
                           game_id=game_id,
                           parent_id=parent_id,
                           game_elements_parents=game_elements_data["game_elements_parents"])

@bp.route("/<int:game_id>/update/game-elements/<int:parent_id>", methods=("GET",))
def update_game_elements_of_the_parent(game_id, parent_id):
    game_title = request.args.get('title')
    parent = request.args.get('parent')
    print('--------------------------------------------------------')
    print(f"game_title: {game_title}")
    print(f"game_id: {game_id}")
    print(f"parent_id: {parent_id}")
    
    game_elements_data = get_game_elements_of_the_parent(game_id, parent_id)
    #game_elements = get_game(game_id)
    return render_template("games/update_ge_of_the_parent.html",
                           game_elements=game_elements_data["game_elements"],
                           game_title=game_title,
                           game_id=game_id,
                           #parent=parent,
                           parent_id=parent_id,
                           game_elements_parents=game_elements_data["game_elements_parents"])

@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a game.

    Ensures that the game exists and that the logged in user is the
    author of the game.
    """
    get_game(id)
    db = get_db()
    db.execute("DELETE FROM game_and_element WHERE game_id = ?", (id,))
    db.execute("DELETE FROM game_link WHERE game_id = ?", (id,))
    db.execute("DELETE FROM game_tag WHERE game_id = ?", (id,))
    db.execute("DELETE FROM game WHERE id = ?", (id,))
    db.commit()
    
    return redirect(url_for("games.index"))

# Links

@bp.route("/game-link/<int:id>/create", methods=("GET", "POST"))
@login_required
def create_link(id):
    """Create a new link for the current user."""
    if request.method == "POST":
        title = request.form["link_title"]
        comment = request.form["comment"]
        error = None

        if not title:
            error = "Link is required."

        if error is not None:
            flash(error)
        else:
            print(title)
            print(g.user["id"])
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO game_link (title, author_id, game_id, comment) VALUES (?, ?, ?, ?)",
                (title, g.user["id"], id, comment),
            )
            
            db.commit()
            return redirect(url_for('games.update', id=id))

    return render_template("games/create.html")


@bp.route("/game-link/<int:id>/delete", methods=("POST",))
@login_required
def delete_link(id):
    """Delete an game link.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    
    db = get_db()
    db.execute("DELETE FROM game_link WHERE id = ?", (id,))
    db.commit()
    
    game_id = request.args.get('game_id')
    print(id)
    print(game_id)
    return redirect(url_for('games.update', id=game_id))
# End Links

# Tags
@bp.route("/game-tag/<int:id>/create", methods=("GET", "POST"))
@login_required
def create_tag(id):
    """Create a new tag for the current user."""
    if request.method == "POST":
        title = request.form["tag_title"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            print(title)
            print(g.user["id"])
            print((id))
            
            post=get_game(id)
            
            db = get_db()
            db.execute(
                "INSERT INTO game_tag (title, author_id, game_id) VALUES (?, ?, ?)",
                (title, g.user["id"], id),
            )
            
            if (post['game']['tags'].find(title) == -1):
                db.execute(
                    "UPDATE game SET tags=? WHERE id=?",
                    (str(post['game']['tags']) + title + ';', id),
                )
            
            db.commit()
            return redirect(url_for('games.update', id=id))

    return render_template("games/update.html")

@bp.route("/game-tag/<int:id>/delete", methods=("POST",))
@login_required
def delete_tag(id):
    """Delete an game tag.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    
    db = get_db()
    db.execute("DELETE FROM game_tag WHERE id = ?", (id,))
    db.commit()
    
    game_id = request.args.get('game_id')
    print(id)
    print(game_id)
    return redirect(url_for('games.update', id=game_id))   
# End Tags


# Game Elements
@bp.route("/<int:id>/game-elements/create", methods=("GET", "POST"))
@login_required
def create_game_element(id):
    """Create a new game element for the current user."""
    if request.method == "POST":
        print('--------------------------------------------------------')
        type_of_id = request.form["type_of_id"]
        print(f'type_of_id = {type_of_id}')
        
        element_id = request.form["element_id"]
        print(f'element_id = {element_id}')
        
        parent_element_id = request.form["parent_element_id"]
        print(f'parent_element_id = {parent_element_id}')
        
        description = request.form["description"]
        print(f'description = {description}')
        
        link = request.form["ge_link"]
        print(f'link = {link}')
        
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
            print((id))
            
            db = get_db()
            if (type_of_id == 'element'):
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description, link, weight, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, g.user["id"], id, description, link, weight, previous_game_element_id),
                )
            else:
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, game_element_id, parent_element_id, author_id, game_id, description, link, weight, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, g.user["id"], id, description, link, weight, previous_game_element_id),
                )
            
            db.commit()
            if parent_element_id:
                game_title = request.args.get('title')
                parent = request.args.get('parent')
                return redirect(url_for("games.update_game_elements_of_the_parent", game_id=id, parent_id=parent_element_id)+"?title="+game_title+"&parent="+parent)
            else:
                return redirect(url_for('games.update', id=id))

    return render_template("games/update.html")

@bp.route("/<int:game_id>/game-elements/<int:ge_id>/delete", methods=("POST",))
@login_required
def delete_game_element(game_id, ge_id):
    """Delete a game element.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    #print('ge_id = ', ge_id)
    #print('game_id = ', game_id)
    
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
        
        return redirect(url_for("games.update", id=game_id, parent_id=parent_id))
    else:
        return redirect(url_for('games.update', id=game_id))   

@bp.route("/<int:game_id>/game-elements/<int:ge_id>/update", methods=("GET", "POST"))
@login_required
def update_game_element(game_id, ge_id):
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
                return redirect(url_for("games.update", id=game_id, parent_id=parent_element_id))
            else:
                return redirect(url_for('games.update', id=game_id))

    return render_template("games/update.html")
# End Game Elements