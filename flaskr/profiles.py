from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from flaskr.extensions import db_SQLAlchemy as db
from flaskr.models import (
    Challenge,
    ChallengeSolution,
    ChallengeSolutionLike,
    GameElementVariant,
    GameElementVariantLike,
)

bp = Blueprint("profiles", __name__, url_prefix="/profile")


def get_user_profile_data(user_id: int) -> dict:
    # ---------------------------------------------------------------
    # 1. Варианты игровых элементов (Game Element Variants)
    # ---------------------------------------------------------------
    # Созданные пользователем
    stmt_created_variants = (
        select(GameElementVariant)
        .where(GameElementVariant.author_id == user_id)
        .options(selectinload(GameElementVariant.likes))
        .order_by(GameElementVariant.created.desc())
    )
    created_variants = db.session.scalars(stmt_created_variants).all()

    # Лайкнутые варианты
    stmt_liked_variants = (
        select(GameElementVariant)
        .options(
            joinedload(GameElementVariant.author),
            selectinload(GameElementVariant.likes),
        )
        .join(GameElementVariantLike)
        .where(GameElementVariantLike.user_id == user_id)
        .order_by(GameElementVariant.created.desc())
    )
    liked_variants = db.session.scalars(stmt_liked_variants).all()

    # ---------------------------------------------------------------
    # 2. Решения челленджей (Challenge Solutions)
    # ---------------------------------------------------------------
    # Созданные пользователем решения
    stmt_created_solutions = (
        select(ChallengeSolution)
        .where(ChallengeSolution.author_id == user_id)
        .options(
            selectinload(ChallengeSolution.challenge),
            selectinload(ChallengeSolution.likes),
        )
        .order_by(ChallengeSolution.created_at.desc())
    )
    created_solutions = db.session.scalars(stmt_created_solutions).all()

    # Лайкнутые решения
    stmt_liked_solutions = (
        select(ChallengeSolution)
        .options(
            joinedload(ChallengeSolution.author),
            selectinload(ChallengeSolution.challenge),
            selectinload(ChallengeSolution.likes),
        )
        .join(ChallengeSolutionLike)
        .where(ChallengeSolutionLike.user_id == user_id)
        .order_by(ChallengeSolution.created_at.desc())
    )
    liked_solutions = db.session.scalars(stmt_liked_solutions).all()

    # ---------------------------------------------------------------
    # 3. Челленджи, созданные пользователем (если авторство открыто)
    # ---------------------------------------------------------------
    stmt_created_challenges = (
        select(Challenge)
        .where(Challenge.author_id == user_id)
        .order_by(Challenge.created_at.desc())
    )
    created_challenges = db.session.scalars(stmt_created_challenges).all()

    # ---------------------------------------------------------------
    # Формируем итоговый словарь со статистикой
    # ---------------------------------------------------------------
    stats = {
        # Варианты элементов
        "variants_needs_revision": [v for v in created_variants if v.status_name == "needs_revision"],
        "variants_pending_review": [v for v in created_variants if v.status_name == "pending_review"],
        "variants_public": [v for v in created_variants if v.status_name == "public"],
        "variants_private": [v for v in created_variants if v.status_name == "private"],
        "variants_liked": liked_variants,
        
        # Решения челленджей
        "solutions_needs_revision": [s for s in created_solutions if s.status_name == "needs_revision"],
        "solutions_pending_review": [s for s in created_solutions if s.status_name == "pending_review"],
        "solutions_public": [s for s in created_solutions if s.status_name == "public"],
        "solutions_private": [s for s in created_solutions if s.status_name == "private"],
        "solutions_liked": liked_solutions,

        # Созданные челленджи
        "created_challenges": created_challenges,
    }

    return stats


@bp.route("/")
@login_required
def index():
    return render_template(
        "profiles/profile.html", stats=get_user_profile_data(current_user.id)
    )