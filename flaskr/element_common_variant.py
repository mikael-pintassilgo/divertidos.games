from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.auth import role_required
from flask_login import login_required, current_user

from flaskr.html_services import sanitize_html
from flaskr.models import ElementCommonVariant
from flaskr.extensions import db_SQLAlchemy

from .db import get_db

bp = Blueprint("element_common_variants", __name__, url_prefix="/element-common-variants")

def get_element_common_variant(e_id):
    db = get_db()
    element_common_variants = db.execute(
        "SELECT description, id, element_id, author_id, created"
        "  FROM element_common_variant"
        " WHERE element_common_variant.element_id = ?",
        (e_id,),
    ).fetchall()

    #if element_common_variants is None:
    #    abort(404, f"There are no common variants for element id {e_id}.")

    return element_common_variants 

@bp.route("/element-common-variant/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create_common_variant():
    """Create a new common variant for the current user."""
    if request.method == "POST":
        description = sanitize_html(request.form.get("description"))
        element_id = request.form.get("element_id")
        
        print('description: ', description)
        print('element_id: ', element_id)
        
        error = None

        if not description:
            error = "Description is required."
        if not element_id:
            error = "Element ID is required."

        if error is not None:
            flash(error)
        else:
            print('current_user.id: ', current_user.id)
            
            db = db_SQLAlchemy.session  # Use the SQLAlchemy session for ORM operations
            
            try:
                # 1. Instantiate the ORM Model object. 
                # This automatically triggers your `default=utc_now` constraint for the 'created' column.
                new_variant = ElementCommonVariant(
                    description=description,
                    element_id=int(element_id),  # Cast to integer for standard SQLite data consistency
                    author_id=current_user.id
                )
                
                # 2. Stage the object into the session and save changes
                db.add(new_variant)
                db.commit()
                
                return redirect(url_for('blog.update_element', id=element_id))
                
            except Exception as e:
                db.rollback()  # Standard SQLAlchemy 2.0 safety measure: roll back if anything breaks
                print(f"Database error occurred: {e}")
                flash("An error occurred while saving the variant.")

    return render_template("blog/update.html")

@bp.route("/element-common-variant/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
def delete_common_variant(id):
    # Safe retrieval of element_id from form data first
    element_id = request.form.get("element_id")
    
    print(f"Deleting variant ID: {id}")
    print(f"Redirecting back to Element ID: {element_id}")
    
    db = db_SQLAlchemy.session
    
    try:
        # 1. Use db.get() for optimized primary key lookups in 2.0
        variant = db.get(ElementCommonVariant, id)
        
        # Alternatively, if you want to use the explicit 2.0 select syntax:
        # variant = db.execute(
        #     select(ElementCommonVariant).where(ElementCommonVariant.id == id)
        # ).scalar_one_or_none()
        
        if variant:
            db.delete(variant)
            db.commit()
            flash("Common variant deleted successfully.")
        else:
            flash("Variant not found or already deleted.")
            
    except Exception as e:
        db.rollback()  # Protect transaction block state
        print(f"Database error during deletion: {e}")
        flash("An error occurred while attempting to delete the variant.")
        
    # Fallback safety: If element_id wasn't in form, redirect safely or handle error
    if not element_id:
        return redirect(url_for('blog.index')) # or wherever your dashboard sits
        
    return redirect(url_for('blog.update_element', id=element_id))
