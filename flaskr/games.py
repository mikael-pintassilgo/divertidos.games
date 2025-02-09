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

bp = Blueprint("games", __name__)

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

    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post with author information
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    db = get_db()

    game = (
        db
        .execute(
            "SELECT g.id, title, body, comment, created, author_id, username"
            "  FROM game g JOIN user u ON g.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
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

    if game is None:
        abort(404, f"Game id {id} doesn't exist.")

    game_data = {
        "game": game,
        "tags": tags,
        "links": links,
    }
    return game_data


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
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
                "INSERT INTO element (title, body, author_id, comment, tags) VALUES (?, ?, ?, ?, ?)",
                (title, body, g.user["id"], comment, tags),
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
                "UPDATE element SET title = ?, body = ?, comment = ?, tags = ? WHERE id = ?", (title, body, comment, tags, id)
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post["element"], tags=post["tags"], links=post["links"])

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a post if the current user is the author."""
    post = get_post(id)
    return render_template("blog/view.html", post=post["element"], tags=post["tags"], links=post["links"])

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