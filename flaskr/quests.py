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

bp = Blueprint("quests", __name__, url_prefix="/quests")

@bp.route("/")
def index():
    barreiro_quests = [{
        'city': 'Barreiro',
        'title': 'Old City',
        'description': 'A walk through the historic part of Barreiro. \nInteresting facts about the city and its inhabitants.',
        'static_link': url_for('static', filename='quests/Barreiro/old-city.html'),
        'price': 'free',
        'start_point': 'Terminal',
    }]
    quests = {
        'barreiro_quests': barreiro_quests,
    }
    
    return render_template("quests/index.html", quests=quests)
