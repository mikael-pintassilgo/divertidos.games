from sqlalchemy import select, or_, desc

import json
from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.models import Game, GameTag, User, GameLink
from flaskr.models import Element, GameAndElement
from flaskr.extensions import db_SQLAlchemy

from sqlalchemy import select, delete

from .auth import user_has_role, role_required
from flask_login import current_user, login_required

from flaskr.db import get_db
from flaskr.blog import get_element_by_title, clean_key

from flaskr.html_services import sanitize_html

bp = Blueprint("games", __name__, url_prefix="/games")

def _index():
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
    
    user_id = current_user.id if current_user.is_authenticated else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False
    
    """Show all the games, most recent first."""
    games = db.execute(
        "SELECT g.id, title, body, created, author_id, username, comment, status"
        "  FROM game g"
        "  JOIN user u ON g.author_id = u.id"
        " WHERE status = 'public' OR ? OR g.author_id = ?"
        " ORDER BY created DESC"
        " LIMIT " + str(offset) + "," + str(limit),
        (user_is_admin, user_id),
    ).fetchall()

    print("user_is_admin: ", user_is_admin)
    for game in games:
        print("game id = " + str(game["id"]) + ", title = " + game["title"] + ", status = " + game["status"])
    
    return render_template("games/index.html", games=games, tag="", currentPage=currentPage)

@bp.route("/")
def index():
    # Pagination logic
    page = request.args.get('page', 1, type=int)
    limit = 10
    
    user_id = current_user.id if current_user.is_authenticated else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False

    # SQLAlchemy 2.0 Select Statement
    # We join User to get the username
    stmt = (
        select(Game)
        .join(User)
        .where(
            or_(
                Game.status == 'public',
                user_is_admin == True,
                Game.author_id == user_id
            )
        )
        .order_by(desc(Game.created))
        .limit(limit)
        .offset((page - 1) * limit)
    )

    # Execute and get results
    games = db_SQLAlchemy.session.execute(stmt).scalars().all()
    
    return render_template("games/index.html", games=games, currentPage=page)

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
            "SELECT g.id, title, body, comment, created, author_id, username, status"
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
            "       ge.element_order,  "
            "       ge.parent_element_id AS parent_element_id,"
            "       CASE WHEN ge.element_order > 0 THEN 1 ELSE 0 END AS order_priority,"
            "       CASE WHEN ge.element_order > 0 THEN ge.element_order ELSE ge.id END AS order_value"
            "  FROM game_and_element AS ge"
            " INNER JOIN element AS e "
            "    ON e.id = ge.element_id AND ge.type_of_id = 'element' "
            "  LEFT JOIN game_and_element AS previous_ge "
            "    ON ge.previous_game_element_id = previous_ge.id"
            " WHERE ge.game_id = ?"
            " ORDER BY order_priority DESC, order_value ASC",
            (id,),
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

    if game_elements:
        game_elements_ids = [the_game_element["ge_id"] for the_game_element in game_elements]
        game_element_variants = db.execute(
            "  SELECT game_element_id,"
            "         COUNT(*) as count"
            "    FROM game_element_variant"
            "   WHERE game_element_id IN (SELECT value FROM json_each(?))"
            "GROUP BY game_element_id",
            (json.dumps(game_elements_ids),)
        ).fetchall()
        
        print("game_element_variants:")
        for row in game_element_variants:
            print(f"  game_element_id={row['game_element_id']}, count={row['count']}")

        game_element_variants_map = {
            row["game_element_id"]: row["count"] 
            for row in game_element_variants
        }
        print("game_element_variants_map:")
        for ge_id, count in game_element_variants_map.items():
            print(f"  game_element_id={ge_id}, count={count}")
        
        
        
        game_elements = [
            dict(element, count=game_element_variants_map.get(element["ge_id"], 0), 
            number_of_variants=game_element_variants_map.get(element["ge_id"], 0))
            for element in game_elements
        ]
        print("\n=== game_elements with extra_info ===")
        for idx, element in enumerate(game_elements):
            print(f"Element {idx}: id={element['ge_id']}, title={element['title']}, count={element['count']}")
        print("=" * 40 + "\n")
        

    # Build a tree structure for game_elements
    def build_element_tree(elements, parent_id=None):
        tree = []
        for element in elements:
            if (element['parent_element_id'] == parent_id or 
                (element['parent_element_id'] is None and parent_id is None) or
                (element['parent_element_id'] == '' and parent_id is None)):
                #print("Building tree for element: ", element['title'])
                children = build_element_tree(elements, element['ge_id'])
                element['children'] = children
                tree.append(element)
        return tree

    game_elements_tree = build_element_tree([dict(element) for element in game_elements])
    #print("game_elements_tree = ", game_elements_tree)

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
@role_required("admin")
def create():
    if request.method == "POST":
        title = request.form["title"]
        body = sanitize_html(request.form["body"])
        comment = sanitize_html(request.form.get("comment", ""))
        error = None

        if not title:
            error = "Title is required."

        if error:
            flash(error)
        else:
            # Create a new Game object
            new_game = Game(
                title=title,
                body=body,
                author_id=current_user.id,
                comment=comment
            )
            db_SQLAlchemy.session.add(new_game)
            db_SQLAlchemy.session.commit()
            return redirect(url_for("games.index"))

    return render_template("games/create.html")

def _create():
    """Create a new game for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        raw_body = request.form["body"]
        body = sanitize_html(raw_body)  # Sanitize the body content to prevent XSS
        raw_comment = request.form["comment"]
        comment = sanitize_html(raw_comment)  # Sanitize the comment content to prevent XSS
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
                (title, body, current_user.id, comment),
            )
            db.commit()
            return redirect(url_for("games.index"))

    return render_template("games/create.html")

#--------------------------------------#
# IMPORT
#--------------------------------------#
# Recursively insert game elements
def _insert_elements(just_check_flag, not_existed_items, db, game_id, data, parent_ge_id=None):
        
    def insert_simple_value(key, value, _parent_ge_id=parent_ge_id):
        # Try to find element by title
        row = get_element_by_title(db, key)
        if row is None:
            # element not found: skip inserting into game_and_element
            not_existed_items.append(clean_key(key))
            return None
        element_id = row["id"]
        
        if not just_check_flag:
            cursor = db.execute(
                "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description) VALUES (?, ?, ?, ?, ?, ?)",
                ("element", element_id, _parent_ge_id, current_user.id, game_id, str(value)),
            )
            current_ge_id = cursor.lastrowid
            return current_ge_id
        else:
            return -1  # Dummy ge_id for just checking
    
    def insert_list(parent_key, value, parent_ge_id):
        for idx, item in enumerate(value):
            if isinstance(item, dict):
                insert_elements(just_check_flag, not_existed_items, db, game_id, item, parent_ge_id)
            else:
                insert_simple_value(parent_key, item, parent_ge_id)
        
    simple_values_as_one_string = ''
    only_simiple_values = True
    
    for _key, value in data.items():
        key = _key.replace('_', ' ').strip()
        if key in ["title", "gameDescription", "description", "game"]:
            continue
        
        if isinstance(value, list):
            current_ge_id = insert_simple_value(key, '') # Create a parent game_element for the list
            if current_ge_id is None:
                continue
            
            insert_list(key, value, current_ge_id)
            only_simiple_values = False
            
        elif isinstance(value, dict):
            only_simiple_values = False
            insert_elements(just_check_flag, not_existed_items, db, game_id, value, parent_ge_id)
            
        else:
            if simple_values_as_one_string:
                simple_values_as_one_string += f" ✦ {clean_key(key).strip()}: {str(value).strip()}"
            else:
                simple_values_as_one_string = f"{clean_key(key).strip()}: {str(value).strip()}"
            insert_simple_value(key, value, parent_ge_id)
            
    if only_simiple_values:
        return simple_values_as_one_string
    else:
        return ''

def _import_game_data(just_check_flag, game_data_json):
    """Import a new game for the current user."""
    db = get_db()
    
    game_info = game_data_json #.get("game", {})
    title = game_info.get("title", "") or game_info.get("game", "")
    body = game_info.get("gameDescription", "")
    
    if not title:
        abort(400, "Game title is required.")
    
    # Insert main game
    if not just_check_flag:
        cursor = db.execute(
            "INSERT INTO game (title, body, author_id, comment) VALUES (?, ?, ?, ?)",
            (title, body, current_user.id, ""),
        )
        game_id = cursor.lastrowid
    else:
        game_id = -1  # Dummy game_id for just checking

    not_existed_items = []
    insert_elements(just_check_flag, not_existed_items, db, game_id, game_info)
    db.commit()
    return game_id, not_existed_items

def insert_elements(just_check_flag, not_existed_items, session, game_id, data, parent_ge_id=None):
    
    def insert_simple_value(key, value, _parent_ge_id=parent_ge_id):
        # 1. Try to find the element definition
        print(f"Searching for element with title: '{key}'")
        element = get_element_by_title(session, key)
        print(f"Element found: {element}")  # Debug output
        
        if element is None:
            not_existed_items.append(clean_key(key))
            return None
        
        if not just_check_flag:
            # 2. Create the junction table entry (GameAndElement)
            new_ge = GameAndElement(
                type_of_id="element",
                element_id=element.id,
                parent_element_id=_parent_ge_id,
                author_id=current_user.id,
                game_id=game_id,
                description=str(value)
            )
            session.add(new_ge)
            session.flush()  # Populates new_ge.id for children to use
            return new_ge.id
        else:
            return -1

    def insert_list(parent_key, value, current_parent_ge_id):
        for item in value:
            if isinstance(item, dict):
                insert_elements(just_check_flag, not_existed_items, session, 
                                game_id, item, current_parent_ge_id)
            else:
                insert_simple_value(parent_key, item, current_parent_ge_id)

    simple_values_as_one_string = ''
    only_simple_values = True
    
    for _key, value in data.items():
        key = _key.replace('_', ' ').strip()
        if key in ["title", "gameDescription", "description", "game"]:
            continue
        
        if isinstance(value, list):
            # Create a parent entry for the list
            current_ge_id = insert_simple_value(key, '') 
            if current_ge_id is not None:
                insert_list(key, value, current_ge_id)
            only_simple_values = False
            
        elif isinstance(value, dict):
            only_simple_values = False
            insert_elements(just_check_flag, not_existed_items, session, 
                            game_id, value, parent_ge_id)
            
        else:
            # Handle the string accumulation logic
            clean_k = clean_key(key).strip()
            val_str = str(value).strip()
            entry = f"{clean_k}: {val_str}"
            
            if simple_values_as_one_string:
                simple_values_as_one_string += f" ✦ {entry}"
            else:
                simple_values_as_one_string = entry
                
            insert_simple_value(key, value, parent_ge_id)

    return simple_values_as_one_string if only_simple_values else ''

def import_game_data(just_check_flag, game_data_json):
    """Import a new game for the current user using SQLAlchemy 2.0."""
    
    game_info = game_data_json
    title = game_info.get("title", "") or game_info.get("game", "")
    body = game_info.get("gameDescription", "")
    
    if not title:
        abort(400, "Game title is required.")
    
    game_id = -1
    not_existed_items = []

    if not just_check_flag:
        # Create a new Game object using your model
        new_game = Game(
            title=title,
            body=body,
            author_id=current_user.id,
            comment=""
        )
        
        # Add to session and flush to get the ID back from the DB
        db_SQLAlchemy.session.add(new_game)
        db_SQLAlchemy.session.flush() 
        game_id = new_game.id
    
    insert_elements(just_check_flag, not_existed_items, db_SQLAlchemy.session, game_id, game_info)
    
    # Final commit if not just checking
    if not just_check_flag:
        db_SQLAlchemy.session.commit()
        
    return game_id, not_existed_items


@bp.route("/import-game", methods=("GET", "POST"))
@login_required
@role_required("admin")
def import_game():
    """Import a new game for the current user."""
    if request.method == "POST":
        game_json = request.form["json_input"]
        just_check_flag = True if request.form.get('just_check_flag') else False
        print('just_check_flag = ' + str(just_check_flag))
        
        error = None

        if not game_json:
            error = "Game JSON is required."

        if error is not None:
            flash(error)
        else:
            game_data_json = json.loads(game_json)
            game_id, not_existed_items = import_game_data(just_check_flag, game_data_json)
            print("not_existed_items: ", not_existed_items)
            
            if just_check_flag:
                return render_template("games/import_game.html", not_existed_items=not_existed_items, game_json=game_json)
            else:
                return redirect(url_for("games.view", id=game_id))

    return render_template("games/import_game.html")
#--------------------------------------#
# END IMPORT
#--------------------------------------#

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

#--------------------------------------#
# EXPORT
#--------------------------------------#
def export_game_data(game_id):
    db = get_db()

    # 1. Get game
    game = db.execute(
        "SELECT title, body FROM game WHERE id = ?",
        (game_id,)
    ).fetchone()

    if game is None:
        return None

    # 2. Load elements
    rows = db.execute(
        """
        SELECT 
            ge.id AS ge_id,
            ge.parent_element_id,
            ge.description,
            ge.type_of_id,
            e.title
        FROM game_and_element ge
        LEFT JOIN element e ON ge.element_id = e.id
        WHERE ge.game_id = ?
        ORDER BY ge.id
        """,
        (game_id,)
    ).fetchall()

    game_elements = [dict(row) for row in rows]

    # --- SAME helper ---
    def get_only_game_elements_of_the_parent(parent_element_id):
        if parent_element_id is None:
            return [
                el for el in game_elements
                if el["parent_element_id"] is None or el["parent_element_id"] == ''
            ]
        else:
            return [
                el for el in game_elements
                if el["parent_element_id"] == parent_element_id
            ]

    # --- Recursive builder ---
    def build_subtree(parent_element_id, parent_title=None):
        sub_elements = get_only_game_elements_of_the_parent(parent_element_id)

        all_elements_has_same_title = True
        sub_elements_has_title_equal_to_parent = True
        
        first_element_title = sub_elements[0]["title"] if sub_elements else None
        for element in sub_elements:
            if element["title"] != first_element_title:
                all_elements_has_same_title = False
                break
        if first_element_title:
            sub_elements_has_title_equal_to_parent = (first_element_title != parent_title)
        
        if all_elements_has_same_title:# and sub_elements_has_title_equal_to_parent:
            result = []
        elif not (parent_element_id is None):
            result = []
        else:
            result = {}
        #duplicates = {}  # key -> list of values

        for element in sub_elements:
            key = (element["title"] or "").strip()
            description = (element["description"] or "").strip()

            children = build_subtree(element["ge_id"], element["title"])

            if children:
                value = children
            else:
                value = description

            if isinstance(result, list):
                result.append({key: value})
            else:
                result[key] = value
            

        # Merge duplicates back as lists
        #for key, values in duplicates.items():
        #    result[key] = values

        return result

    # 3. Final JSON
    game_json = {
        "title": game["title"],
        "gameDescription": game["body"]
    }

    game_json.update(build_subtree(None))

    return json.dumps(game_json, indent=4)

@bp.route("/<int:id>/get_full_description_JSON", methods=("GET", "POST"))
def get_full_description_JSON(id):
    data_JSON = ''
    data_JSON = export_game_data(id)
    game_data = get_game(id)

    return render_template("games/full_description.html",
                           game=game_data["game"],
                           full_description=data_JSON,)
#--------------------------------------#
# END EXPORT
#--------------------------------------#

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
@role_required("admin")
def update_game(id):
    """Update a post if the current user is the author."""
    game_data = get_game(id)
    
    user_id = current_user.id
    if game_data["game"]["author_id"] != user_id and not user_has_role(user_id, "admin"):
        abort(403)
    
    parent_id = request.args.get('parent_id')
    print(f"229 parent_id = {parent_id}")
    element_id = request.args.get('element_id')
    
    if parent_id and parent_id != 'None' and parent_id != '':
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
        body = sanitize_html(body)  # Sanitize the body content to prevent XSS
        comment = request.form["comment"]
        comment = sanitize_html(comment)  # Sanitize the comment content to prevent XSS

        if user_has_role(user_id, "admin"):
            status = request.form["status"] or "private" # Admin can update status
        else:
            status = game_data["game"]["status"] # Non-admin cannot change status
        
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE game SET title = ?, body = ?, comment = ?, status = ?"
                "WHERE id = ?",
                (title, body, comment, status, id)
            )
            db.commit()
            return redirect(url_for("games.index"))

    return render_template("games/update.html",
                           game=game_data["game"],
                           tags=game_data["tags"],
                           links=game_data["links"],
                           game_elements=game_elements,
                           game_elements_parents=game_elements_parents,
                           parent_id=parent_id,
                           element_id=element_id,)

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a game if the current user is the author."""
    print('Viewing game id = ', id)
    game_data = get_game(id)
    user_id = current_user.id if current_user.is_authenticated else None
    if game_data["game"]["status"] != "public" and game_data["game"]["author_id"] != user_id and not user_has_role(user_id, "admin"):
        abort(403)
    
    parent_id = request.args.get('parent_id')
    print(f"230 parent_id = {parent_id}")
    if parent_id and parent_id != 'None' and parent_id != '':
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
            "       ge.element_order,  "
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
            "       ge.element_order,  "
            "       ge.parent_element_id"
            "  FROM game_and_element AS ge"
            "  LEFT JOIN game_and_element AS previous_ge "
            "    ON ge.previous_game_element_id = previous_ge.id"
            " WHERE ge.type_of_id = 'game_element' AND ge.game_id = ? AND ge.parent_element_id = ?"
    )
    
def get_game_elements_of_the_parent(game_id, parent_element_id):
    db = get_db()

    if parent_element_id == 'None' or parent_element_id == '' or parent_element_id is None:
        _parent_element_id = None
    else:
        _parent_element_id = int(parent_element_id)
    
    game_elements = (
        db
        .execute(
            get_sql_for_elements_of_the_parent(),
            (game_id, _parent_element_id, game_id, _parent_element_id,),
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
@role_required("admin")
def delete_game(id):
    """Delete a game and its relations."""
    
    # 1. Fetch the game or abort 404 (Modern Session.get approach)
    game = db_SQLAlchemy.session.get(Game, id)
    if game is None:
        abort(404, f"Game id {id} doesn't exist.")
        
    # 2. Delete the game
    db_SQLAlchemy.session.delete(game)

    # 3. Commit the transaction
    db_SQLAlchemy.session.commit()
    
    return redirect(url_for("games.index"))

# Links

@bp.route("/game-link/<int:id>/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
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
            print(current_user.id)
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO game_link (title, author_id, game_id, comment) VALUES (?, ?, ?, ?)",
                (title, current_user.id, id, comment),
            )
            
            db.commit()
            return redirect(url_for('games.update_game', id=id))

    return render_template("games/create.html")


@bp.route("/game-link/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
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
    return redirect(url_for('games.update_game', id=game_id))
# End Links

# Tags
@bp.route("/game-tag/<int:id>/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
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
            print(current_user.id)
            print((id))
            
            post=get_game(id)
            
            db = get_db()
            db.execute(
                "INSERT INTO game_tag (title, author_id, game_id) VALUES (?, ?, ?)",
                (title, current_user.id, id),
            )
            
            if (post['game']['tags'].find(title) == -1):
                db.execute(
                    "UPDATE game SET tags=? WHERE id=?",
                    (str(post['game']['tags']) + title + ';', id),
                )
            
            db.commit()
            return redirect(url_for('games.update_game', id=id))

    return render_template("games/update.html")

@bp.route("/game-tag/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
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
    return redirect(url_for('games.update_game', id=game_id))   
# End Tags


# Game Elements
@bp.route("/<int:id>/game-elements/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
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
            print(current_user.id)
            print((id))
            
            db = get_db()
            if (type_of_id == 'element'):
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, element_id, parent_element_id, author_id, game_id, description, link, weight, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, current_user.id, id, description, link, weight, previous_game_element_id),
                )
            else:
                db.execute(
                    "INSERT INTO game_and_element (type_of_id, game_element_id, parent_element_id, author_id, game_id, description, link, weight, previous_game_element_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (type_of_id, element_id, parent_element_id, current_user.id, id, description, link, weight, previous_game_element_id),
                )
            
            db.commit()
            if parent_element_id:
                game_title = request.args.get('title')
                parent = request.args.get('parent')
                return redirect(url_for("games.update_game_elements_of_the_parent", game_id=id, parent_id=parent_element_id)+"?title="+game_title+"&parent="+parent)
            else:
                return redirect(url_for('games.update_game', id=id))

    return render_template("games/update.html")

@bp.route("/<int:game_id>/game-elements/<int:ge_id>/delete", methods=("POST",))
@login_required
@role_required("admin")
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
        
        return redirect(url_for("games.update_game", id=game_id, parent_id=parent_id))
    else:
        return redirect(url_for('games.update_game', id=game_id))   

@bp.route("/<int:game_id>/game-elements/<int:ge_id>/update", methods=("GET", "POST"))
@login_required
@role_required("admin")
def update_game_element(game_id, ge_id):
    """Update an existing game element for the current user."""
    db = get_db()
    game_element = db.execute(
        "SELECT * FROM game_and_element WHERE id = ? AND author_id = ?",
        (ge_id, current_user.id),
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
            print(current_user.id)
            print((game_id))
            
            db = get_db()
            if (type_of_id == 'element'):
                db.execute(
                    "UPDATE game_and_element SET type_of_id = ?, element_id = ?,"\
                    "parent_element_id = ?, author_id = ?, game_id = ?, description = ?, previous_game_element_id = ?, " \
                    "weight = ?, link = ? " \
                    "WHERE id = ?",
                    (type_of_id, element_id, parent_element_id, current_user.id, game_id, description, previous_game_element_id, weight, link, ge_id),
                )
            else:
                db.execute(
                    "UPDATE game_and_element SET type_of_id = ?, game_element_id = ?, parent_element_id = ?, author_id = ?, " \
                    "game_id = ?, description = ?, previous_game_element_id = ?, weight = ?, link = ? WHERE id = ?",
                    (type_of_id, element_id, parent_element_id, current_user.id, game_id, description, previous_game_element_id, weight, link, ge_id),
                )

            db.commit()
            if parent_element_id:
                game_title = request.args.get('title')
                parent = request.args.get('parent')
                return redirect(url_for("games.update_game", id=game_id, parent_id=parent_element_id))
            else:
                return redirect(url_for('games.update_game', id=game_id))

    return render_template("games/update.html")
# End Game Elements