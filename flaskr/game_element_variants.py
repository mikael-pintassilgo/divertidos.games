from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.auth import role_required, user_has_role
from flask_login import current_user, login_required

from flaskr.db import get_db
from flaskr.html_services import sanitize_html
from flaskr.extensions import db_SQLAlchemy
from flaskr.models import GameElementVariant, GameElementVariantLike, VariantStatus, User

from sqlalchemy import select, update, func, delete
from sqlalchemy import or_, and_


bp = Blueprint("game_element_variants", __name__, url_prefix="/game-element-variants")

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

def get_game_element_variants(ge_id):
    user_id = current_user.id if current_user.is_authenticated else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False

    # 1. Scalar subquery for the count (most efficient for sorting)
    like_count_stmt = (
        select(func.count(GameElementVariantLike.id))
        .where(GameElementVariantLike.variant_id == GameElementVariant.id)
        .scalar_subquery()
    )

    # 2. Build the main query
    stmt = (
        select(
            GameElementVariant,
            User.username.label("author_name"),
            like_count_stmt.label("likes_count") # We select the count directly
        )
        .join(User, GameElementVariant.author_id == User.id, isouter=True)
        .where(GameElementVariant.game_element_id == ge_id)
        .where(
            or_(
                GameElementVariant.status_name == 'public',
                user_is_admin,
                GameElementVariant.author_id == user_id
            )
        )
        # Order by likes first, then newest
        .order_by(like_count_stmt.desc(), GameElementVariant.created.desc())
    )

    # 4. Execute and get scalars (the objects)
    rows = db_SQLAlchemy.session.execute(stmt).all()
    
    # Unpack on the server side into a list of dictionaries
    game_element_variants = []
    for variant, author_name, likes_count in rows:
        game_element_variants.append({
            "obj": variant,             # Keep the object for likes/relationships
            "id": variant.id,           # Explicit ID
            "author_id": variant.author_id,           # Explicit ID
            "title": variant.title,
            "author_name": author_name,
            "likes_count": likes_count,
            "likes": variant.likes,       # Pass the list of like objects for template logic
            "status_name": variant.status_name,
            "admin_feedback": variant.admin_feedback,
            "created": variant.created
        })

    return game_element_variants

def _get_game_element_variants(ge_id):
    user_id = current_user.id if current_user.is_authenticated else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False

    # 1. Build the Query
    # We select the columns we need. SQLAlchemy will handle the JOIN.
    stmt = (
        select(
            GameElementVariant,
            User.username.label("author_name")
        )
        .join(User, GameElementVariant.author_id == User.id, isouter=True) # isouter=True makes it a LEFT JOIN
        .where(GameElementVariant.game_element_id == ge_id)
        .where(
            or_(
                GameElementVariant.status_name == 'public',
                user_is_admin,               # If True, this part of OR is always met
                GameElementVariant.author_id == user_id
            )
        )
    )

    # 2. Execute
    # .mappings() allows you to access columns by name like a dictionary (e.g., row['title'])
    result = db_SQLAlchemy.session.execute(stmt).mappings().all()

    print('game_element_variants: ', result)

    return result

@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new variant for the current user."""
    if request.method == "POST":
        # 1. Extract and Sanitize Data
        title = sanitize_html(request.form.get("variant_title"))
        game_element_id = request.form.get("game_element_id")
        game_id = request.form.get("game_id")
        
        action = request.form.get('action')
        if action == 'submit_for_publication':
            # Logic for public publication
            status_name='pending_review'
        else: #if action == 'save_private':
            # Logic for private saving
            status_name='private'

    
        # 2. Validation
        error = None
        if not title:
            error = "Title is required."
        elif not game_element_id:
            error = "Game element ID is required."
        elif not game_id:
            error = "Game ID is required."
        
        if error:
            flash(error)
            # You might want to return the template here instead of falling through
        else:
            # 3. SQLAlchemy 2.0 Insert
            try:
                new_variant = GameElementVariant(
                    title=title,
                    author_id=current_user.id,
                    game_element_id=game_element_id,
                    game_id=game_id,
                    target_type='game_and_element',
                    status_name=status_name
                )
                
                db_SQLAlchemy.session.add(new_variant)
                db_SQLAlchemy.session.commit()
                
                # 4. Handle Redirection logic
                is_view = request.form.get("is_view", "").lower() == "true"
                if is_view:
                    return redirect(url_for("game_elements.view", ge_id=game_element_id, game_id=game_id))
                
                return redirect(url_for('game_elements.update', ge_id=game_element_id))
            
            except Exception as e:
                db_SQLAlchemy.session.rollback()
                flash("An error occurred while saving the variant.")
                print(f"Database error: {e}")

    # Fallback to the update page (ensure game_element_id is available)
    ge_id = request.args.get('ge_id') or request.form.get('game_element_id')
    return render_template("game_elements/update.html", ge_id=ge_id)

@bp.route("/<int:id>/publish", methods=("GET", "POST"))
@login_required
@role_required("admin")
def publish(id):
    # If using POST for the action (standard for state changes)
    if request.method == "POST":
        # In Flask, the 'id' from the URL is already passed as the function argument
        game_element_variant_id = id
        
        if not game_element_variant_id:
            flash("Game element ID is required.")
        else:
            try:
                # SQLAlchemy 2.0 Update Statement
                stmt = (
                    update(GameElementVariant)
                    .where(GameElementVariant.id == game_element_variant_id)
                    .values(status_name='public')
                )
                
                db_SQLAlchemy.session.execute(stmt)
                db_SQLAlchemy.session.commit()
                
                flash(f"Variant #{id} has been published.")
                
            except Exception as e:
                db_SQLAlchemy.session.rollback()
                print(f"Error publishing variant: {e}")
                flash("An error occurred during publication.")

    # Redirect to the pending reviews list
    return redirect(url_for('services.pending_reviews'))

@bp.route("/<int:id>/return_for_revision", methods=("POST",))
@login_required
@role_required("admin")
def return_for_revision(id):
    """Admin returns a variant to the author for fixes."""
    
    # Get the feedback from the form (usually a textarea in your admin panel)
    feedback = request.form.get("admin_feedback")
    
    if not feedback or not feedback.strip():
        flash("Please provide feedback so the author knows what to fix.")
        return redirect(url_for('services.pending_reviews'))

    try:
        # SQLAlchemy 2.0 Update Statement
        stmt = (
            update(GameElementVariant)
            .where(GameElementVariant.id == id)
            .values(
                status_name='needs_revision',
                admin_feedback=sanitize_html(feedback) # Keep your data clean
            )
        )
        
        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()
        
        # Check if the row actually existed
        if result.rowcount > 0:
            flash(f"Variant #{id} has been returned to the author for revision.")
        else:
            flash("Variant not found.")
            
    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error returning variant: {e}")
        flash("An error occurred while updating the variant status.")

    return redirect(url_for('services.pending_reviews'))

@bp.route("/<int:id>/resubmit", methods=("POST",))
@login_required
def resubmit(id):
    """Author updates their variant and sends it back to the admin for review."""
    
    # 1. Get and Sanitize the updated title
    title = sanitize_html(request.form.get("variant_title"))
    game_element_id = request.form.get("game_element_id")
    
    if not title:
        flash("Title is required to resubmit.")
        return redirect(request.referrer or url_for('main.index'))

    try:
        # 2. Update the record
        # Security: ensure current user IS the author and status IS 'needs_revision'
        stmt = (
            update(GameElementVariant)
            .where(
                and_(
                    GameElementVariant.id == id,
                    GameElementVariant.author_id == current_user.id,
                    GameElementVariant.status_name == 'needs_revision'
                )
            )
            .values(
                title=title,             # Update the title with sanitized input
                status_name='pending_review',
                admin_feedback=None      # Clear feedback as the author has addressed it
            )
        )
        
        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()
        
        if result.rowcount > 0:
            flash("Variant updated and resubmitted for review!")
        else:
            flash("Action denied: You can only resubmit your own variants that require revision.")
            
    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error during resubmission: {e}")
        flash("A database error occurred.")

    # Redirect back to the element or update page
    is_view = request.form.get("is_view", "").lower() == "true"
    if is_view:
        game_id = request.form.get("game_id")
        return redirect(url_for("game_elements.view", ge_id=game_element_id, game_id=game_id))
    return redirect(url_for('game_elements.update', ge_id=game_element_id))
    
@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete_variant(id):
    """Delete a variant. Only the author or an admin can delete."""
    
    game_element_id = request.form.get("game_element_id")
    user_id = current_user.id
    user_is_admin = user_has_role(user_id, "admin") # Assuming you have this helper

    try:
        # SQLAlchemy 2.0 Delete Statement with Security Check
        # A user can delete if: (ID matches) AND (they are the author OR they are an admin)
        stmt = (
            delete(GameElementVariant)
            .where(
                and_(
                    GameElementVariant.id == id,
                    or_(
                        GameElementVariant.author_id == user_id,
                        user_is_admin
                    )
                )
            )
        )
        
        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()
        
        if result.rowcount > 0:
            flash("Variant deleted successfully.")
        else:
            flash("Delete failed: Variant not found or you do not have permission.")
            
    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error deleting variant: {e}")
        flash("An error occurred while trying to delete the variant.")

    game_id = request.form.get("game_id")
    is_view = request.form.get("is_view", "").lower() == "true"
    if is_view:
        return redirect(url_for("game_elements.view", ge_id=game_element_id, game_id=game_id))
    return redirect(url_for('game_elements.update', ge_id=game_element_id))

@bp.route("/variant/<int:id>/toggle_like", methods=("POST",))
@login_required
def toggle_like(id):
    user_id = current_user.id
    
    # 1. Check if the like already exists
    stmt = select(GameElementVariantLike).where(
        GameElementVariantLike.user_id == user_id,
        GameElementVariantLike.variant_id == id
    )
    existing_like = db_SQLAlchemy.session.execute(stmt).scalar_one_or_none()

    try:
        if existing_like:
            # 2. "Take back" the like
            db_SQLAlchemy.session.delete(existing_like)
            flash("Removed from your favorites.", "info")
        else:
            # 3. Add a new like
            new_like = GameElementVariantLike(user_id=user_id, variant_id=id)
            db_SQLAlchemy.session.add(new_like)
            flash("You liked this variant!", "success")
        
        db_SQLAlchemy.session.commit()
    except Exception as e:
        db_SQLAlchemy.session.rollback()
        flash("An error occurred.")

    # Redirect back to the page the user was on
    return redirect(request.form.get('next') or url_for('main.index'))