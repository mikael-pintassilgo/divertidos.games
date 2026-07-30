from urllib.parse import urlparse
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from flask_login import current_user, login_required

from flaskr.auth import role_required, user_has_role
from flaskr.html_services import sanitize_html
from flaskr.extensions import db_SQLAlchemy
from flaskr.models import ChallengeSolution, ChallengeSolutionLike, User, Challenge

from sqlalchemy import select, update, func, delete, or_, and_, literal

bp = Blueprint("challenge_solutions", __name__, url_prefix="/challenge-solutions")


def is_safe_url(target):
    """Проверка URL на безопасность для предотвращения Open Redirect."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def get_challenge_solutions(challenge_id):
    """
    Получает список решений для конкретного челленджа.
    Сортирует по количеству лайков, затем по дате создания.
    """
    user_id = current_user.id if current_user.is_authenticated else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False

    # 1. Подзапрос для подсчета лайков
    like_count_stmt = (
        select(func.count(ChallengeSolutionLike.id))
        .where(ChallengeSolutionLike.solution_id == ChallengeSolution.id)
        .scalar_subquery()
    )

    # 2. Флаг "лайкнул ли текущий пользователь"
    if user_id:
        is_liked_stmt = select(1).where(
            and_(
                ChallengeSolutionLike.solution_id == ChallengeSolution.id,
                ChallengeSolutionLike.user_id == user_id
            )
        ).exists()
    else:
        # Для незалогиненных пользователей ставим жесткий False через literal()
        is_liked_stmt = literal(False)

    # 3. Основной запрос
    stmt = (
        select(
            ChallengeSolution,
            User.username.label("author_name"),
            like_count_stmt.label("likes_count"),
            is_liked_stmt.label("is_liked_by_user")
        )
        .join(User, ChallengeSolution.author_id == User.id, isouter=True)
        .where(ChallengeSolution.challenge_id == challenge_id)
        .where(
            or_(
                ChallengeSolution.status_name == 'public',
                user_is_admin,
                and_(user_id is not None, ChallengeSolution.author_id == user_id)
            )
        )
        .order_by(like_count_stmt.desc(), ChallengeSolution.created_at.desc())
    )

    rows = db_SQLAlchemy.session.execute(stmt).all()

    solutions = []
    for solution, author_name, likes_count, is_liked in rows:
        solutions.append({
            "obj": solution,
            "id": solution.id,
            "challenge_id": solution.challenge_id,
            "author_id": solution.author_id,
            "content": solution.content,
            "author_name": author_name or "Unknown",
            "likes_count": likes_count,
            "is_liked_by_user": bool(is_liked),
            "status_name": solution.status_name,
            "admin_feedback": getattr(solution, 'admin_feedback', None),
            "created_at": solution.created_at,
            "updated_at": solution.updated_at
        })

    return solutions


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create_solution():
    """Создание нового решения для челленджа."""
    if request.method == "POST":
        content = sanitize_html(request.form.get("content", ""))
        raw_challenge_id = request.form.get("challenge_id")

        action = request.form.get('action')
        status_name = 'pending_review' if action == 'submit_for_publication' else 'private'

        # Валидация
        error = None
        if not content or not content.strip():
            error = "Solution content is required."
        elif not raw_challenge_id or not raw_challenge_id.isdigit():
            error = "Valid Challenge ID is required."

        if error:
            flash(error, "error")
        else:
            try:
                challenge_id = int(raw_challenge_id)
                new_solution = ChallengeSolution(
                    content=content,
                    author_id=current_user.id,
                    challenge_id=challenge_id,
                    status_name=status_name
                )

                db_SQLAlchemy.session.add(new_solution)
                db_SQLAlchemy.session.commit()

                flash("Your solution has been saved!", "success")
                return redirect(url_for("challenges.view", id=challenge_id))

            except Exception as e:
                db_SQLAlchemy.session.rollback()
                flash("An error occurred while saving the solution.", "error")
                print(f"Database error: {e}")

    challenge_id = request.args.get('challenge_id') or request.form.get('challenge_id')
    if challenge_id and challenge_id.isdigit():
        return redirect(url_for("challenges.view", id=int(challenge_id)))
    return redirect(url_for("challenges.index"))


@bp.route("/<int:id>/toggle_like", methods=("POST",))
@login_required
def toggle_like(id):
    """Переключение лайка (лайкнуть / убрать лайк)."""
    user_id = current_user.id
    challenge_id = request.form.get('challenge_id')

    stmt = select(ChallengeSolutionLike).where(
        ChallengeSolutionLike.user_id == user_id,
        ChallengeSolutionLike.solution_id == id
    )
    existing_like = db_SQLAlchemy.session.execute(stmt).scalar_one_or_none()

    try:
        if existing_like:
            db_SQLAlchemy.session.delete(existing_like)
            flash("Removed from your favorites.", "info")
        else:
            new_like = ChallengeSolutionLike(user_id=user_id, solution_id=id)
            db_SQLAlchemy.session.add(new_like)
            flash("You liked this solution!", "success")

        db_SQLAlchemy.session.commit()
    except Exception as e:
        db_SQLAlchemy.session.rollback()
        flash("An error occurred while updating likes.", "error")

    target = request.form.get('next') or request.referrer
    if target and is_safe_url(target):
        return redirect(target)
    return redirect(url_for("challenges.view", id=challenge_id))


@bp.route("/<int:id>/change_status", methods=("POST",))
@login_required
def change_status(id):
    """
    Allows the author to toggle solution status between 'private' and 'pending_review'.
    """
    new_status = request.form.get("status")
    challenge_id = request.form.get("challenge_id")
    
    # 1. Strict whitelist validation
    ALLOWED_STATUSES = {"private", "pending_review"}
    if new_status not in ALLOWED_STATUSES:
        print(f"Attempted to set invalid status: {new_status}")
        flash("Invalid status selected.", "error")
        return redirect(request.referrer or url_for("challenges.index"))

    user_id = current_user.id
    user_is_admin = user_has_role(user_id, "admin")

    try:
        # 2. Update status safely
        # Only allow changing status if the user owns it (or is admin) 
        # and the solution isn't already published.
        stmt = (
            update(ChallengeSolution)
            .where(
                and_(
                    ChallengeSolution.id == id,
                    or_(
                        ChallengeSolution.author_id == user_id,
                        user_is_admin
                    ),
                    # Prevent users from switching a published solution back to private/pending
                    ChallengeSolution.status_name != "public" 
                )
            )
            .values(
                status_name=new_status,
                updated_at=func.now()
            )
        )

        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()

        if result.rowcount > 0:
            msg = (
                "Solution submitted for review!"
                if new_status == "pending_review"
                else "Solution status updated to private."
            )
            flash(msg, "success")
        else:
            flash("Could not update status. Solution not found, permission denied, or already published.", "error")

    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error changing solution status: {e}")
        flash("A database error occurred while updating status.", "error")

    # Safe redirect
    target = request.referrer
    if target and is_safe_url(target):
        return redirect(target)
    if challenge_id and challenge_id.isdigit():
        return redirect(url_for("challenges.view", id=int(challenge_id)))
    return redirect(url_for("challenges.index"))


@bp.route('/<int:id>/update', methods=['POST'])
@login_required
def update_solution(id):
    solution = ChallengeSolution.query.get_or_404(id)
    if solution.author_id != current_user.id:
        abort(403)

    solution.content = request.form.get('content')
    action = request.form.get('action')

    if action == 'submit_for_publication':
        solution.status_name = 'pending_review'
    else:
        solution.status_name = 'private'

    db_SQLAlchemy.session.commit()
    return redirect(url_for('challenges.view', id=solution.challenge_id))


@bp.route("/<int:id>/publish", methods=("POST",))
@login_required
@role_required("admin")
def publish_solution(id):
    """Публикация решения администратором."""
    try:
        stmt = (
            update(ChallengeSolution)
            .where(ChallengeSolution.id == id)
            .values(status_name='public')
        )

        db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()

        flash(f"Solution #{id} has been published.", "success")

    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error publishing solution: {e}")
        flash("An error occurred during publication.", "error")

    return redirect(request.referrer or url_for('services.pending_reviews'))


@bp.route("/<int:id>/return_for_revision", methods=("POST",))
@login_required
@role_required("admin")
def return_for_revision(id):
    """Возврат решения пользователю на доработку."""
    feedback = request.form.get("admin_feedback")
    print(f"Rturning solution #{id} for revision with feedback: {feedback}")  # Debugging line
    
    if not feedback or not feedback.strip():
        flash("Please provide feedback so the author knows what to fix.", "warning")
        return redirect(request.referrer or url_for('services.pending_reviews'))

    try:
        stmt = (
            update(ChallengeSolution)
            .where(ChallengeSolution.id == id)
            .values(
                status_name='needs_revision',
                admin_feedback=sanitize_html(feedback)
            )
        )

        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()

        if result.rowcount > 0:
            flash(f"Solution #{id} has been returned for revision.", "info")
        else:
            flash("Solution not found.", "error")

    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error returning solution: {e}")
        flash("An error occurred while updating the status.", "error")

    return redirect(request.referrer or url_for('services.pending_reviews'))


@bp.route("/<int:id>/resubmit", methods=("POST",))
@login_required
def resubmit(id):
    """Повторная отправка решения после исправления замечаний."""
    content = sanitize_html(request.form.get("content", ""))
    challenge_id = request.form.get("challenge_id")

    if not content or not content.strip():
        flash("Content is required to resubmit.", "warning")
        return redirect(request.referrer or url_for('challenges.index'))

    try:
        stmt = (
            update(ChallengeSolution)
            .where(
                and_(
                    ChallengeSolution.id == id,
                    ChallengeSolution.author_id == current_user.id,
                    ChallengeSolution.status_name == 'needs_revision'
                )
            )
            .values(
                content=content,
                status_name='pending_review',
                admin_feedback=None,
                updated_at=func.now()
            )
        )

        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()

        if result.rowcount > 0:
            flash("Solution updated and resubmitted for review!", "success")
        else:
            flash("Action denied: You can only resubmit your own solutions requiring revision.", "error")

    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error during resubmission: {e}")
        flash("A database error occurred.", "error")

    return redirect(url_for("challenges.view", id=challenge_id))


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete_solution(id):
    """Удаление решения автором или администратором."""
    challenge_id = request.form.get("challenge_id")
    user_id = current_user.id
    user_is_admin = user_has_role(user_id, "admin")

    try:
        stmt = (
            delete(ChallengeSolution)
            .where(
                and_(
                    ChallengeSolution.id == id,
                    or_(
                        ChallengeSolution.author_id == user_id,
                        user_is_admin
                    )
                )
            )
        )

        result = db_SQLAlchemy.session.execute(stmt)
        db_SQLAlchemy.session.commit()

        if result.rowcount > 0:
            flash("Solution deleted successfully.", "success")
        else:
            flash("Delete failed: Solution not found or permission denied.", "error")

    except Exception as e:
        db_SQLAlchemy.session.rollback()
        print(f"Error deleting solution: {e}")
        flash("An error occurred while deleting the solution.", "error")

    return redirect(url_for("challenges.view", id=challenge_id))
