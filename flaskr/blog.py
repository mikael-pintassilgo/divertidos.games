import re

from flask import Blueprint, jsonify
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import abort

from werkzeug.exceptions import abort

from collections import defaultdict

from flaskr.composition_of_elements import get_composition_of_element
from flaskr.html_services import sanitize_html
from flaskr.models import CompositionOfElement, Element, ElementLink, ElementTag, Game, GameAndElement, Tag, User
from flaskr.auth import role_required
from flask_login import login_required
from flaskr.db import get_db
from flaskr.extensions import db_SQLAlchemy

from sqlalchemy import insert, select, func, and_, or_, asc, delete
from sqlalchemy import update
from sqlalchemy.orm import aliased


bp = Blueprint("blog", __name__, url_prefix="/elements")


def get_elements(session, _page, tags_list=None, search_term=''):
    # 1. Pagination Setup
    current_page = int(_page) if _page is not None else 1
    limit = 12
    offset = (current_page - 1) * limit
    tags_list = tags_list or []

    # Aliases for the self-join on Element (parent)
    ParentElement = aliased(Element)
    
    # Base query for the elements
    # We use func.substr to mimic your SQL: substr(body, 1, 150)
    base_query = (
        select(
            Element.id,
            Element.parent_id,
            Element.title,
            ParentElement.title.label("parent_title"),
            func.substr(Element.body, 1, 170).label("body"),
            Element.created,
            Element.author_id,
            User.username,
            Element.tags
        )
        .join(User, Element.author_id == User.id)
        .outerjoin(ParentElement, Element.parent_id == ParentElement.id)
    )

    # 2. Logic Branching
    if tags_list:
        # Step A: Find IDs that have ALL the tags (HAVING count logic)
        tag_subquery = (
            select(ElementTag.element_id)
            .where(ElementTag.title.in_(tags_list))
            .group_by(ElementTag.element_id)
            .having(func.count(func.distinct(ElementTag.title)) == len(tags_list))
        )
        
        # Step B: Filter main query by those IDs
        query = base_query.where(Element.id.in_(tag_subquery))

    elif search_term:
        # Case-insensitive-ish pattern matching
        pattern = f"%{search_term}%"
        query = base_query.where(
            or_(
                Element.title.ilike(pattern),
                Element.body.ilike(pattern),
                Element.comment.ilike(pattern) # Assuming comment exists on Element
            )
        )
        
    else:
        # Default: Just the base query
        query = base_query

    # 3. Finalize: Order and Paginate
    final_query = (
        query.order_by(Element.title.asc())
        .limit(limit)
        .offset(offset)
    )

    # Execute
    results = session.execute(final_query).fetchall()
    
    return results, current_page, limit
    
@bp.route("/")
def index():
    # 1. Extract and sanitize inputs
    tag_title = request.args.get('tag')
    search_term = request.args.get('search', '').strip()
    page = request.args.get('page', type=int, default=1)
    
    # 2. Logic for tags (Cleaning up the 'if False' and cookie logic)
    # Priority: URL Param 'tag' > Cookie Tags > Empty List
    tags_list = []
    if tag_title:
        tags_list = [tag_title]
    else:
        cookie_tags = request.cookies.get('tags')
        if cookie_tags:
            # Filter out empty strings if the cookie ends in '%%'
            tags_list = [t for t in cookie_tags.split('%%') if t]

    # Debugging (Using f-strings for 2026 standards)
    print(f"Method: {request.method} | Search: {search_term} | Tags: {tags_list}")

    # 3. Call the SQLAlchemy 2.0 version of get_elements
    # We pass db.session directly
    posts, current_page, limit = get_elements(
        session=db_SQLAlchemy.session, 
        _page=page, 
        tags_list=tags_list, 
        search_term=search_term
    )
        
    return render_template(
        "blog/index.html", 
        posts=posts, 
        tag=tag_title, 
        tags=tags_list, 
        currentPage=current_page, 
        search_term=search_term,
        limit=limit
    )

def clean_key(text):
    # Adds space between camelCase and capitalizes
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text).title()

from sqlalchemy import select, func

def get_element_by_title(session, title):
    # 1. Build the query using func for TRIM and LOWER
    # SELECT id FROM element WHERE trim(lower(title)) = trim(lower(:title))
    stmt = (
        select(Element.id)
        .where(
            func.trim(func.lower(Element.title)) == func.trim(func.lower(title))
        )
    )
    
    # 2. Execute and fetch the first result
    result = session.execute(stmt).fetchone()
    
    # Returns a Row object (e.g., (1,)) or None if not found
    return result

@bp.route("/get_elements_for_selection", methods=("GET", "POST"))
@login_required
def get_elements_for_selection():
    # 1. Use Flask's built-in type conversion for the page
    page = request.args.get('page', type=int, default=1)
    search_term = request.args.get('search', '').strip()
    
    # 2. Call the updated get_elements function
    # We pass an empty list for tags as per your original logic
    elements, current_page, _limit = get_elements(
        session=db_SQLAlchemy.session, 
        _page=page, 
        tags_list=[], 
        search_term=search_term
    )
    
    # Debugging
    print(f"Elements found: {len(elements)} (Page: {current_page})")
    
    # 3. Format results for JSON
    # Note: SQLAlchemy 2.0 Rows allow attribute access (e.id)
    return jsonify({
        "elements": [
            {
                "id": e.id, 
                "title": e.title, 
                "body": e.body
            } for e in elements
        ],
        "currentPage": current_page
    })

def get_post(session, id, check_author=True):
    # 1. Aliases for self-joins and related tables
    ParentElement = aliased(Element, name="parent")
    
    # 2. Main Element Query
    element_stmt = (
        select(
            Element.id,
            Element.title,
            Element.parent_id,
            ParentElement.title.label("parent_title"),
            Element.body,
            Element.comment,
            Element.created,
            Element.author_id,
            User.username,
            Element.tags
        )
        .join(User, Element.author_id == User.id)
        .outerjoin(ParentElement, Element.parent_id == ParentElement.id)
        .where(Element.id == id)
    )
    element = session.execute(element_stmt).fetchone()

    if element is None:
        abort(404, f"Element id {id} doesn't exist.")

    if check_author and element.author_id != current_user.id:
        abort(403)

    # 3. Composition / Part Of Query
    # Logic: Join Element through the bridge table composition_of_element
    part_of_stmt = (
        select(Element.id, Element.title, Element.body)
        .join(CompositionOfElement, CompositionOfElement.element_id == Element.id)
        .where(CompositionOfElement.subelement_id == id)
    )
    part_of = session.execute(part_of_stmt).fetchall()

    # 4. Tags Query
    tags_stmt = (
        select(
            ElementTag.id, 
            Tag.title, 
            Tag.comment, 
            Tag.id.label("tag_id")
        )
        .join(Tag, ElementTag.tag_id == Tag.id)
        .where(ElementTag.element_id == id)
        .order_by(Tag.title.asc())
    )
    tags = session.execute(tags_stmt).fetchall()

    # 5. Links Query
    links_stmt = (
        select(ElementLink.id, ElementLink.title, ElementLink.comment)
        .where(ElementLink.element_id == id)
        .order_by(ElementLink.created.asc())
    )
    links = session.execute(links_stmt).fetchall()

    # 6. Games Query (Distinct)
    # 6.1. Execute the query without grouping/aggregation
    games_stmt = (
        select(
            Game.id.label("g_id"), 
            Game.title, 
            Game.body,
            GameAndElement.element_id,  # Included for grouping 
            GameAndElement.description
        )
        .join(GameAndElement, Game.id == GameAndElement.game_id)
        .where(GameAndElement.element_id == id)
    )
    raw_rows = session.execute(games_stmt).fetchall()

    if False:
        games = raw_rows
    else:
        # 6.2. Process the results in Python
        grouped_data = defaultdict(lambda: {"descriptions": [], "title": "", "body": ""})

        for row in raw_rows:
            # Creating a composite key
            group_key = (row.g_id, row.element_id)
            
            # Store attributes (they should be identical for the same group_key)
            grouped_data[group_key]["title"] = row.title
            grouped_data[group_key]["body"] = row.body
            
            if row.body:
                grouped_data[group_key]["descriptions"].append(str(row.description))

        # 6.3. Finalize the list with concatenated strings
        games = []
        for (g_id, e_id), data in grouped_data.items():
            games.append({
                "g_id": g_id,
                "element_id": e_id,
                "title": data["title"],
                "body": data["body"],
                "description": "<br>- ".join(data["descriptions"])
            })
    
    # 7. Get composition of element (subelements)
    composition_of_element = get_composition_of_element(session, id)

    # 8. Return a unified dictionary
    return {
        "element": element,
        "composition_of_element": composition_of_element,
        "part_of": part_of,
        "tags": tags,
        "links": links,
        "games": games,
    }

@bp.route("/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        # 1. Extract and sanitize data
        title = request.form.get("title", "").strip()
        body = sanitize_html(request.form.get("body", ""))
        comment = request.form.get("comment", "").strip()
        tags = "" # Placeholder for tags logic
        
        # Handle parent_id: Convert empty string to None/NULL
        raw_parent_id = request.form.get("parent_id")
        parent_id = int(raw_parent_id) if raw_parent_id and raw_parent_id.isdigit() else None

        error = None
        if not title:
            error = "Title is required."

        if error:
            flash(error)
        else:
            new_element = Element(
                parent_id=parent_id,
                title=title,
                body=body,
                author_id=current_user.id,
                comment=comment,
                tags=tags
            )

            # Add object to session
            db_SQLAlchemy.session.add(new_element)

            # Commit to DB
            db_SQLAlchemy.session.commit()

            # SQLite automatically populates the primary key
            new_id = new_element.id

            return redirect(url_for("blog.view", id=new_id))

    return render_template("blog/create.html")

@bp.route("/element-tag/<int:id>/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create_tag(id):
    """Create a new tag for the current user."""
    if request.method == "POST":
        tag_id = request.form["tag_id"]
        error = None

        if not tag_id:
            error = "tag_id is required."

        if error is not None:
            flash(error)
        else:
            print('tag_id: ', tag_id)
            print('current_user.id: ',current_user.id)
            print('id: ', id)
            
            db = get_db()
            db.execute(
                "INSERT INTO element_tag (tag_id, author_id, element_id) VALUES (?, ?, ?)",
                (tag_id, current_user.id, id),
            )
            
            db.commit()
            return redirect(url_for('blog.update_element', id=id))

    return render_template("blog/create.html")

@bp.route("/element-link/<int:id>/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create_link(id):
    """Create a new link for the current user."""
    if request.method == "POST":
        title = request.form["link_title"]
        comment = request.form["link_comment"]
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
                "INSERT INTO element_link (title, comment, author_id, element_id) VALUES (?, ?, ?, ?)",
                (title, comment, current_user.id, id),
            )
            
            db.commit()
            return redirect(url_for('blog.update_element', id=id))

    return render_template("blog/create.html")

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
@role_required("admin")
def update_element(id):
    """Update a post if the current user is the author."""
    # 1. Fetch existing data (validates existence and authorship)
    post_data = get_post(db_SQLAlchemy.session, id, check_author=True)

    if request.method == "POST":
        # 2. Extract and sanitize form data
        title = request.form.get("title", "").strip()
        body = sanitize_html(request.form.get("body", ""))
        comment = sanitize_html(request.form.get("comment", "")).strip()
        tags = request.form.get("tags", "").strip()
        
        # Handle parent_id: Convert empty string to None for the DB
        raw_parent_id = request.form.get("parent_id")
        parent_id = int(raw_parent_id) if raw_parent_id and raw_parent_id.isdigit() else None

        error = None
        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            # 3. Execute the Update
            stmt = (
                update(Element)
                .where(Element.id == id)
                .values(
                    parent_id=parent_id,
                    title=title,
                    body=body,
                    comment=comment,
                    tags=tags
                )
            )
            db_SQLAlchemy.session.execute(stmt)
            db_SQLAlchemy.session.commit()
            
            return redirect(url_for("blog.view", id=id))

    # 4. Render template using the same unpacking logic as the view route
    return render_template(
        "blog/update.html", 
        post=post_data["element"], 
        **post_data
    )

from flask import render_template
# from your_app.models import get_post

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    """View a post and all its related data."""
    
    # 1. Fetch the unified post object using the SQLAlchemy session
    # We set check_author=False here because usually "viewing" 
    # doesn't require ownership unless it's a private draft.
    post_data = get_post(db_SQLAlchemy.session, id, check_author=False)
    
    # 2. Render using dictionary unpacking (**post_data)
    # This automatically maps:
    # element -> post (manual override below), tags, links, games, etc.
    return render_template(
        "blog/view.html", 
        post=post_data["element"], 
        **post_data
    )

@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
def delete_element(id):
    """Delete a post.

    Ensures that the post exists and that the logged-in user is the
    author of the post (handled by get_post).
    """
    # 1. Validation: get_post will abort(404) if missing 
    # and abort(403) if current_user.id != element.author_id
    get_post(db_SQLAlchemy.session, id, check_author=True)
    
    # 2. Execution: Using the SQLAlchemy 2.0 delete construct
    stmt = delete(Element).where(Element.id == id)
    db_SQLAlchemy.session.execute(stmt)
    
    # 3. Commit the transaction
    db_SQLAlchemy.session.commit()
    
    return redirect(url_for("blog.index"))

@bp.route("/element-tag/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
def delete_element_tag(id):
    """Delete an element tag linkage.
    
    Ensures that the tag exists and that the logged-in user is the 
    author (or has permission).
    """
    # 1. (Optional but recommended) Security Check
    # Verify the tag exists and the user owns it before deleting
    tag_to_delete = db_SQLAlchemy.session.execute(
        select(ElementTag).where(ElementTag.id == id)
    ).scalar_one_or_none()

    if tag_to_delete is None:
        flash("Tag linkage not found.")
    elif tag_to_delete.author_id != current_user.id:
        flash("You are not authorized to delete this tag.")
    else:
        # 2. Execute the Delete
        stmt = (
            delete(ElementTag)
            .where(ElementTag.id == id)
            # You can also add .where(ElementTag.author_id == current_user.id) 
            # here as a double safety measure
        )
        db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()

    # 3. Handle Redirect
    # Getting element_id from query params as in your original code
    element_id = request.args.get('element_id')
    
    return redirect(url_for('blog.update_element', id=element_id))   

@bp.route("/element-link/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
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
    return redirect(url_for('blog.update_element', id=element_id))

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