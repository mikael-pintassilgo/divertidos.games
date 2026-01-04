import json
import os
import re

from flask import Blueprint, jsonify
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required
from .db import get_db

bp = Blueprint("blog", __name__)

def get_elements(_page, tags_list, search_term=''):
    db = get_db()
    
    if (_page == None):
        currentPage = 1
    else:
        currentPage = int(_page)
    limit = 12
    offset = (currentPage - 1) * limit
    
    if (tags_list == None):
        tags_list = []
    
    print('currentPage = ' + str(currentPage))
    print('offset = ' + str(offset))
    print('limit = ' + str(limit))
    
    if len(tags_list):
        elements_ids = db.execute(
            "SELECT e.id"
            "  FROM element_tag et"
            " INNER JOIN element e ON et.element_id = e.id"
            " WHERE et.title in (SELECT value FROM json_each(?))"
            " GROUP BY e.id"
            " HAVING count(DISTINCT et.title) = ?",
            (json.dumps(tags_list), len(tags_list)),
        ).fetchall()
        
        if elements_ids == None:
            posts = []
        else:        
            posts = db.execute(
                "SELECT e.id, e.parent_id, e.title, substr(e.body, 1, 150) as body, e.created, e.author_id, u.username, e.tags"
                "  FROM element e"
                "  JOIN user u ON e.author_id = u.id"
                " WHERE e.id in (SELECT value FROM json_each(?))"
                " ORDER BY e.title ASC"
                " LIMIT " + str(offset) + "," + str(limit),
                (json.dumps([row[0] for row in elements_ids]),),
            ).fetchall()        
    
    elif (search_term != '' and search_term is not None):
        search_pattern = f"%{search_term}%"
        posts = db.execute(
            "SELECT e.id, e.parent_id, e.title as title, parent.title as parent_title, substr(e.body, 1, 170) as body, e.created, e.author_id, u.username, e.tags"
            "  FROM element e"
            "  JOIN user u ON e.author_id = u.id"
            "  LEFT JOIN element parent ON e.parent_id = parent.id"
            " WHERE e.title LIKE ? OR e.body LIKE ? OR e.comment LIKE ?"
            " ORDER BY e.title ASC"
            " LIMIT " + str(offset) + "," + str(limit),
            (search_pattern, search_pattern, search_pattern),
        ).fetchall()    
    else:
        #tag_title = ""
        #tags_list = []
        """Show all the posts, most recent first."""
        posts = db.execute(
            "SELECT e.id, e.parent_id, e.title as title, parent.title as parent_title, substr(e.body, 1, 170) as body, e.created, e.author_id, u.username, e.tags"
            "  FROM element e"
            "  JOIN user u ON e.author_id = u.id"
            "  LEFT JOIN element parent ON e.parent_id = parent.id"
            " ORDER BY e.title ASC"
            " LIMIT " + str(offset) + "," + str(limit)
        ).fetchall()
        
    return posts, currentPage
    
@bp.route("/")
def index():
    tag_title = request.args.get('tag')
    print('rquest.method = ' + str(request.method))
    search_term = request.args.get('search', '')
    print('search_term = ' + str(search_term))
    coockie_tags = request.cookies.get('tags')
    
    if (tag_title):
        tags_list = [tag_title,]
    else:
        # tags in coockie
        if coockie_tags:
            tags_list = coockie_tags.split('%%')
        else:
            tags_list = []
    
    print('coockie_tags = ' + str(coockie_tags))
    print('tags_list = ' + str(tags_list))
    # end tags in coockie
    
    _page = request.args.get('page')
    posts, currentPage = get_elements(_page, tags_list, search_term=search_term)
        
    return render_template("blog/index.html", posts=posts, tag=tag_title, tags=tags_list, currentPage=currentPage, search_term=search_term)

@bp.route("/services", methods=("GET",))
@login_required
def services():
    return render_template("services/services.html", messages=[])

def clean_key(text):
    # Adds space between camelCase and capitalizes
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text).title()

def get_element_by_title(db, title):
    element = db.execute(
        "SELECT id FROM element WHERE title = ?",
        (clean_key(title),),
    ).fetchone()
    return element

def add_element_from_dict(db, title, body, parent_id=None):
    if body.strip() == '' or title.strip() == '':
        return
                
    # Check if element already exists
    existing_element = db.execute(
        "SELECT id FROM element WHERE title = ?",
        (title,)
    ).fetchone()

    if not existing_element:
        cursor = db.execute(
            "INSERT INTO element (title, body, parent_id, author_id) VALUES (?, ?, ?, ?)",
            (title, body, parent_id, g.user["id"])
        )
        db.commit()
        return cursor.lastrowid
    
    return existing_element['id']

def load_dictionary_recursive(ids, db, dict_data, parent_id=None):
    for key, value in dict_data.items():
            #body = item.get('description', item.get('body', ''))
            if isinstance(value, str):
                id = add_element_from_dict(db, clean_key(key), value, parent_id)
                ids.append({ 'id': id, 'title': clean_key(key), 'body': value })
                #messages.append({'key': clean_key(key), 'value': value, 'id': id})
            elif isinstance(value, dict):
                description = value.get('description', '')
                parent_id = add_element_from_dict(db, clean_key(key), description, parent_id)
                ids.append({ 'id': parent_id, 'title': clean_key(key), 'body': description })
                #messages.append({'key': clean_key(key), 'value': description, 'id': parent_id})
                
                for sub_key, sub_value in value.items():
                    if clean_key(sub_key) != 'Description':
                        if isinstance(sub_value, str):
                            id = add_element_from_dict(db, clean_key(sub_key), sub_value, parent_id)
                            ids.append({ 'id': id, 'title': clean_key(sub_key), 'body': sub_value })
                        elif isinstance(sub_value, dict):
                            load_dictionary_recursive(ids, db, sub_value, parent_id=parent_id)
                        #messages.append({'sub_key': clean_key(sub_key), 'sub_value': sub_value, 'id': id})
                        
            else:
                pass
                #messages.append({'key': clean_key(key), 'value': 'Unsupported data type'})

@bp.route("/services/<path:service_name>", methods=("POST",))
@login_required
def load_dictionary(service_name):
    if service_name == 'load_dictionary':
        db = get_db()
        json_input = request.form.get('json_input')
        if not json_input:
            # Load dictionary logic here
            dict_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../flaskr/static/dictionary/dictionary.json'))
            with open(dict_path, 'r') as f:
                dict_data = json.load(f)
        else:
            try:
                dict_data = json.loads(json_input)
            except json.JSONDecodeError as e:
                messages = ['Invalid JSON input: ' + str(e)]
                return render_template("services/services.html", messages=messages)

        messages = []
        ids = []
        try:
            load_dictionary_recursive(ids, db, dict_data)
            messages.append('Dictionary loaded successfully.')
        except Exception as e:
            messages.append('Error loading dictionary: ' + str(e))
            
        return render_template("services/services.html", messages=messages, ids=ids)
    else:
        return render_template("services/services.html", messages=['Unknown service requested: ' + service_name])

@bp.route("/get_elements_for_selection", methods=("GET", "POST"))
@login_required
def get_elements_for_selection():
    _page = request.args.get('page')
    if (_page == None):
        _page = 1
    elements, currentPage = get_elements(_page, [])
    print('elements = ', elements)
    print('elements length = ', len(elements))
    return jsonify({"elements": [{"id": e["id"], "title": e["title"], "body": e["body"]} for e in elements]})

def get_post(id, check_author=True):
    """Get a post and its author by id.

    Checks that the id exists and optionally that the current user is
    the author.

    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post with author information
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    db = get_db()

    element = (
        db
        .execute(
            "SELECT e.id, e.title as title, e.parent_id, parent.title as parent_title, e.body, e.comment, e.created, e.author_id, u.username, e.tags"
            "  FROM element e"
            "  JOIN user u ON e.author_id = u.id"
            "  LEFT JOIN element parent ON e.parent_id = parent.id"
            " WHERE e.id = ?",
            (id,),
        )
        .fetchone()
    )
    sub_elements = (
        db
        .execute(
            "SELECT e.id, e.title as title, e.body, e.comment, e.created, e.author_id, u.username"
            "  FROM element e"
            "  JOIN user u ON e.author_id = u.id"
            " WHERE e.parent_id = ?",
            (id,),
        )
        .fetchall()
    )
    tags = (
        db
        .execute(
            "SELECT t.id, title, comment"
            "  FROM element_tag t JOIN user u ON t.author_id = u.id"
            " WHERE t.element_id = ?"
            " ORDER BY created ASC",
            (id,),
        ).fetchall()
    )
    links = (
        db
        .execute(
            "SELECT l.id, title, comment"
            "  FROM element_link l JOIN user u ON l.author_id = u.id"
            " WHERE l.element_id = ?"
            " ORDER BY created ASC",
            (id,),
        ).fetchall()
    )
    games = (
        db
        .execute(
            "SELECT DISTINCT g.id as g_id, g.title, g.body"
            "  FROM game g JOIN user u ON g.author_id = u.id"
            " INNER JOIN game_and_element ge ON g.id = ge.game_id"
            " WHERE ge.element_id = ?",
            (id,),
        ).fetchall()
    )
    print('games = ' + str(games))
    
    if element is None:
        abort(404, f"Element id {id} doesn't exist.")

    post = {
        "element": element,
        "sub_elements": sub_elements,
        "tags": tags,
        "links": links,
        "games": games,
    }
    return post


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        comment = request.form["comment"]
        parent_id = request.form["parent_id"]
        tags = "" #request.form["tags"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO element (parent_id, title, body, author_id, comment, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (parent_id, title, body, g.user["id"], comment, tags),
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/create.html")

@bp.route("/element-tag/<int:id>/create", methods=("GET", "POST"))
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
            
            post=get_post(id)
            
            db = get_db()
            db.execute(
                "INSERT INTO element_tag (title, author_id, element_id) VALUES (?, ?, ?)",
                (title, g.user["id"], id),
            )
            
            if (post['element']['tags'].find(title) == -1):
                db.execute(
                    "UPDATE element SET tags=? WHERE id=?",
                    (str(post['element']['tags']) + title + ';', id),
                )
            
            db.commit()
            return redirect(url_for('blog.update', id=id))

    return render_template("blog/create.html")

@bp.route("/element-link/<int:id>/create", methods=("GET", "POST"))
@login_required
def create_link(id):
    """Create a new link for the current user."""
    if request.method == "POST":
        title = request.form["link_title"]
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
                "INSERT INTO element_link (title, author_id, element_id) VALUES (?, ?, ?)",
                (title, g.user["id"], id),
            )
            
            db.commit()
            return redirect(url_for('blog.update', id=id))

    return render_template("blog/create.html")

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    post = get_post(id)

    if request.method == "POST":
        parent_id = request.form["parent_id"]
        title = request.form["title"]
        body = request.form["body"]
        comment = request.form["comment"]
        tags = request.form["tags"]

        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE element SET parent_id = ?, title = ?, body = ?, comment = ?, tags = ? WHERE id = ?", (parent_id, title, body, comment, tags, id)
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post["element"], tags=post["tags"], links=post["links"])

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a post if the current user is the author."""
    post = get_post(id)
    return render_template("blog/view.html", post=post["element"], tags=post["tags"], links=post["links"], games=post["games"], sub_elements=post["sub_elements"])

@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    get_post(id)
    db = get_db()
    db.execute("DELETE FROM element WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("blog.index"))

@bp.route("/element-tag/<int:id>/delete", methods=("POST",))
@login_required
def delete_element_tag(id):
    """Delete an element tag.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    
    db = get_db()
    db.execute("DELETE FROM element_tag WHERE id = ?", (id,))
    db.commit()
    
    element_id = request.args.get('element_id')
    print(id)
    print(element_id)
    return redirect(url_for('blog.update', id=element_id))   

@bp.route("/element-link/<int:id>/delete", methods=("POST",))
@login_required
def delete_element_link(id):
    """Delete an element link.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    
    db = get_db()
    db.execute("DELETE FROM element_link WHERE id = ?", (id,))
    db.commit()
    
    element_id = request.args.get('element_id')
    print(id)
    print(element_id)
    return redirect(url_for('blog.update', id=element_id))

@bp.route("/authors")
@login_required
def authors():
    """View a list of authors."""
    db = get_db()
    authors = db.execute(
        "SELECT username"
        "  FROM user",
    ).fetchall()
    
    for val in authors:
        print(val["username"])

    return render_template('blog/authors.html', authors=authors)