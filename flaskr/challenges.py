import json

from sqlalchemy import select, or_, desc, delete


from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from werkzeug.exceptions import abort

from flaskr.models import Challenge, User
from flaskr.extensions import db_SQLAlchemy

from .auth import user_has_role, role_required
from flask_login import current_user, login_required

from flaskr.html_services import sanitize_html

bp = Blueprint("challenges", __name__, url_prefix="/challenges")

@bp.route("/")
def index():
    # Pagination logic
    page = request.args.get('page', 1, type=int)
    limit = 10
    
    user_id = current_user.id if current_user.is_authenticated else None
    user_is_admin = user_has_role(user_id, "admin") if user_id else False

    # SQLAlchemy 2.0 Select Statement
    # We join User to get the username
    stmt = (
        select(Challenge)
        .join(User)
        .where(
            or_(
                Challenge.status_name == 'public',
                user_is_admin == True,
                Challenge.author_id == user_id
            )
        )
        .order_by(desc(Challenge.created_at))
        .limit(limit)
        .offset((page - 1) * limit)
    )

    # Execute and get results
    challenges = db_SQLAlchemy.session.execute(stmt).scalars().all()
    
    return render_template("challenges/index.html", challenges=challenges, currentPage=page)

@bp.route("/create", methods=("GET", "POST"))
@login_required
@role_required("admin")
def create_challenge():
    if request.method == "POST":
        user_id = current_user.id
        if not user_has_role(user_id, "admin"):
            flash("You are not authorized to update this challenge.")
            return redirect(url_for("challenges.index"))
        
        title = request.form["title"]
        description = sanitize_html(request.form["description"])
        html_text = sanitize_html(request.form["html_text"])
        error = None

        if not title:
            error = "Title is required."

        if error:
            flash(error)
        else:
            # Create a new Challenge object
            new_challenge = Challenge(
                title=title,
                description=description,
                author_id=current_user.id,
                html_text=html_text,
                status_name="private"  # Default status for new challenges
            )
            db_SQLAlchemy.session.add(new_challenge)
            db_SQLAlchemy.session.commit()
            return redirect(url_for("challenges.index"))

    return render_template("challenges/create.html")

@bp.route("/<int:id>/view", methods=("GET", "POST"))
def view(id):
    return render_template("challenges/view.html")

"""
def get_challenge(session: Session, challenge_id: int) -> Challenge:
    stmt = (
        select(Challenge)
        .where(Challenge.challenge_id == challenge_id)
        .options(
            joinedload(Challenge.author),         # Подгружаем автора челленджа
            joinedload(Challenge.solutions)       # Подгружаем список решений
            .joinedload(Solution.author)          # ...и сразу авторов для каждого решения
        )
    )
    
    # Выполняем запрос. unique() обязателен при joinedload для связок один-ко-многим
    challenge = session.scalars(stmt).unique().one_or_none()
    
    # Если в базе ничего нет — сразу отдаем 404 через Flask
    if challenge is None:
        abort(404, description=f"Challenge with ID {challenge_id} not found.")
        
    # Превращаем JSON-строку из SQLite в удобный для шаблонизатора список
    if challenge.images_json:
        try:
            challenge.images = json.loads(challenge.images_json)
        except json.JSONDecodeError:
            challenge.images = []
    else:
        challenge.images = []
        
    return challenge
"""

def get_challenge_for_update(challenge_id: int) -> Challenge:
    stmt = (
        select(Challenge)
        .where(Challenge.id == challenge_id)
        .join(User, Challenge.author_id == User.id)
    )
    
    challenge = db_SQLAlchemy.session.scalars(stmt).one_or_none()
    
    if challenge is None:
        abort(404, description=f"Challenge with ID {challenge_id} not found.")
        
    if challenge.images_json:
        try:
            challenge.images = json.loads(challenge.images_json)
        except json.JSONDecodeError:
            challenge.images = []
    else:
        challenge.images = []
        
    return challenge

@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
@role_required("admin")
def update_challenge(id):
    user_id = current_user.id
    
    if request.method == "POST":
        if not user_has_role(user_id, "admin"):
            flash("You are not authorized to update this challenge.")
            return redirect(url_for("challenges.index"))

        title = request.form["title"]
        description = request.form["description"]
        html_text = request.form["html_text"]
        description = sanitize_html(description)  # Sanitize the description content to prevent XSS
        html_text = sanitize_html(html_text)  # Sanitize the HTML text content to prevent XSS

        error = None

        if user_has_role(user_id, "admin"):
            status = request.form["status"] or "private" # Admin can update status
        else:
            #status = game_data["game"]["status"]
            error = "Non-admin cannot change status"
        
        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            return redirect(url_for("challenges.index"))

    return render_template("challenges/update.html", challenge=get_challenge_for_update(id))

@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
@role_required("admin")
def delete_challenge(id):
    """Delete a challenge and its relations."""
    
    # 1. Fetch the challenge or abort 404 (Modern Session.get approach)
    challenge = db_SQLAlchemy.session.get(Challenge, id)
    if challenge is None:
        abort(404, f"Challenge id {id} doesn't exist.")
        
    # 2. Delete the challenge
    db_SQLAlchemy.session.delete(challenge)

    # 3. Commit the transaction
    db_SQLAlchemy.session.commit()
    
    return redirect(url_for("challenges.index"))