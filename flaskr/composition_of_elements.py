from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from .auth import login_required, role_required
from .db import get_db

bp = Blueprint("composition_of_element", __name__, url_prefix="/composition-of-elements")

def get_composition_of_element(e_id):
    db = get_db()
    composition_of_element = db.execute(
        "SELECT ce.*,"
        "       e.title AS subelement_title,"
        "       e.body AS subelement_body"
        "  FROM composition_of_element AS ce LEFT JOIN element AS e ON ce.subelement_id = e.id"
        " WHERE ce.element_id = ?",
        (e_id,),
    ).fetchall()

    if composition_of_element is None:
        abort(404, f"There are no subelements for element id {e_id}.")

    return composition_of_element 

@bp.route("/composition-of-elements/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create():
    """Create a new row in composition_of_element for the current user."""
    if request.method == "POST":
        element_id = request.form["element_id"]
        subelement_id = request.form["subelement_id"]
        
        print('element_id: ', element_id)
        print('subelement_id: ', subelement_id)
        
        error = None

        if not element_id:
            error = "element_id is required."
        if not subelement_id:
            error = "subelement_id is required."

        db = get_db()
        element = db.execute(
            "SELECT author_id FROM element WHERE id = ?",
            (element_id,),
        ).fetchone()

        if element is None:
            error = "Element not found."
        elif element["author_id"] != g.user["id"]:
            error = "You are not authorized to modify this element."

        if error is not None:
            flash(error)
        else:
            
            print(g.user["id"])
            print((id))
            
            db = get_db()
            db.execute(
                "INSERT INTO composition_of_element (element_id, subelement_id, author_id) VALUES (?, ?, ?)",
                (element_id, subelement_id, g.user["id"]),
            )
            
            db.commit()
            return redirect(url_for('blog.update', id=element_id))

    return render_template("blog/view.html", id=element_id)

@bp.route("/composition-of-elements/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
def delete(id):
    if request.method == "POST":
        db = get_db()
        db.execute(
            "DELETE FROM composition_of_element WHERE id = ? AND author_id = ?",
            (id, g.user["id"]),
        )
        db.commit()
        
        element_id = request.form["element_id"]
        print(element_id)
        return redirect(url_for('blog.update', id=element_id))
