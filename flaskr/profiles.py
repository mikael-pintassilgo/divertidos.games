from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from flaskr.extensions import db_SQLAlchemy as db
from flaskr.models import GameElementVariant, GameElementVariantLike, GameElementVariant, GameElementVariantLike, User
from flask_login import login_required, current_user

from flask import Blueprint
from flask import g
from flask import render_template
from flask import request

bp = Blueprint("profiles", __name__, url_prefix="/profile")

def get_user_profile_data(user_id):

    stmt_created = (
        select(GameElementVariant)
        .where(GameElementVariant.author_id == user_id)
        .options(selectinload(GameElementVariant.likes)) # Чтобы видеть кол-во лайков
        .order_by(GameElementVariant.created.desc())
    )
    created_variants = db.session.execute(stmt_created).scalars().all()

    stmt_liked = (
        select(GameElementVariant)
        .join(GameElementVariantLike)
        .where(GameElementVariantLike.user_id == user_id)
        .options(selectinload(GameElementVariant.likes))
        .order_by(GameElementVariant.created.desc())
    )
    stmt_liked = (
        select(GameElementVariant)
        .options(
            joinedload(GameElementVariant.author), # Automatically joins User table
            selectinload(GameElementVariant.likes)
        )
        .join(GameElementVariantLike)
        .where(GameElementVariantLike.user_id == user_id)
        .order_by(GameElementVariant.created.desc())
    )
    liked_variants = db.session.execute(stmt_liked).scalars().all()

    stats = {
        'needs_revision': [v for v in created_variants if v.status_name == 'needs_revision'],
        'pending_review': [v for v in created_variants if v.status_name == 'pending_review'],
        'public': [v for v in created_variants if v.status_name == 'public'],
        'private': [v for v in created_variants if v.status_name == 'private'],
        'liked': liked_variants
    }
    
    return stats

@bp.route("/")
@login_required
def index():
    print("Rendering profile page")
    return render_template("profiles/profile.html", stats=get_user_profile_data(current_user.id))