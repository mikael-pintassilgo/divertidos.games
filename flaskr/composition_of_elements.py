from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import abort

from werkzeug.exceptions import abort

from flaskr.models import CompositionOfElement, Element
from flaskr.auth import role_required
from flask_login import login_required
from flaskr.db import get_db
from flaskr.extensions import db_SQLAlchemy

from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy import insert

bp = Blueprint("composition_of_element", __name__, url_prefix="/composition-of-elements")

def get_composition_of_element(session, e_id):
    # Select all columns from composition_of_element + joined columns
    stmt = (
        select(
            CompositionOfElement.id,
            CompositionOfElement.subelement_id,
            CompositionOfElement.element_id,
            Element.title.label("subelement_title"),
            Element.body.label("subelement_body")            
        )
        .outerjoin(Element, CompositionOfElement.subelement_id == Element.id)
        .where(CompositionOfElement.element_id == e_id)
    )
    
    results = session.execute(stmt).fetchall()

    return results

@bp.route("/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create_element_of_composition():
    element_id = request.form.get("element_id") # Safer than direct access
    
    if request.method == "POST":
        subelement_id = request.form.get("subelement_id")
        error = None

        if not element_id:
            error = "element_id is required."
        elif not subelement_id:
            error = "subelement_id is required."

        if error is None:
            # 1. Check permissions (Scalar returns just the value of the first column)
            element_author = db_SQLAlchemy.session.execute(
                select(Element.author_id).where(Element.id == element_id)
            ).scalar()

            if element_author is None:
                error = "Element not found."
            elif element_author != current_user.id:
                error = "You are not authorized to modify this element."

        if error:
            flash(error)
        else:
            # 2. Perform Insert
            new_comp = insert(CompositionOfElement).values(
                element_id=element_id,
                subelement_id=subelement_id,
                author_id=current_user.id
            )
            db_SQLAlchemy.session.execute(new_comp)
            db_SQLAlchemy.session.commit()
            
            return redirect(url_for('blog.update_element', id=element_id))

    return render_template("blog/view.html", id=element_id)

@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
def delete_element_of_composition(id):
    # Perform the deletion with an explicit author check
    stmt = (
        delete(CompositionOfElement)
        .where(CompositionOfElement.id == id)
        .where(CompositionOfElement.author_id == current_user.id)
    )
    
    db_SQLAlchemy.session.execute(stmt)
    db_SQLAlchemy.session.commit()
    
    # Grab the redirect ID from the form
    element_id = request.form.get("element_id")
    return redirect(url_for('blog.update_element', id=element_id))