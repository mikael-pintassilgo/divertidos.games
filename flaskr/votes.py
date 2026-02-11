from flask import Blueprint, request, jsonify
from flask import g

from .db import get_db
from .auth import login_required

vote_api = Blueprint("vote_api", __name__)

@vote_api.route("/api/vote", methods=["POST"])
@login_required
def vote_toggle():
    user_id = g.user["id"]
    
    data = request.get_json(silent=True) or {}
    target_type = data.get("target_type")
    target_id = data.get("target_id")
    action = data.get("action")  # "like" or "dislike"

    if target_type not in ("game", "game_and_element"):
        return jsonify({"error": "Invalid target_type"}), 400

    if not isinstance(target_id, int):
        return jsonify({"error": "Invalid target_id"}), 400

    if action not in ("like", "dislike"):
        return jsonify({"error": "Invalid action"}), 400

    new_vote_value = 1 if action == "like" else -1

    db = get_db()

    # Find existing vote
    existing = db.execute(
        """
        SELECT id, vote_value
        FROM vote
        WHERE user_id = ? AND target_type = ? AND target_id = ?
        """,
        (user_id, target_type, target_id),
    ).fetchone()

    if existing is None:
        # Insert new vote
        db.execute(
            """
            INSERT INTO vote (user_id, target_type, target_id, vote_value)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, target_type, target_id, new_vote_value),
        )
        db.commit()
        status = "created"

    else:
        old_value = existing["vote_value"]

        if old_value == new_vote_value:
            # Toggle off (remove vote)
            db.execute(
                "DELETE FROM vote WHERE id = ?",
                (existing["id"],),
            )
            db.commit()
            status = "removed"

        else:
            # Switch vote (dislike -> like or like -> dislike)
            db.execute(
                """
                UPDATE vote
                SET vote_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_vote_value, existing["id"]),
            )
            db.commit()
            status = "updated"

    # Return updated totals
    totals = db.execute(
        """
        SELECT
            SUM(CASE WHEN vote_value = 1 THEN 1 ELSE 0 END) AS likes,
            SUM(CASE WHEN vote_value = -1 THEN 1 ELSE 0 END) AS dislikes
        FROM vote
        WHERE target_type = ? AND target_id = ?
        """,
        (target_type, target_id),
    ).fetchone()

    return jsonify({
        "status": status,
        "target_type": target_type,
        "target_id": target_id,
        "likes": totals["likes"] or 0,
        "dislikes": totals["dislikes"] or 0,
    }), 200

@vote_api.route("/api/vote/status", methods=["GET"])
def vote_status():
    user_id = g.user["id"]

    target_type = request.args.get("target_type")
    target_id = request.args.get("target_id", type=int)

    if target_type not in ("game", "game_and_element"):
        return jsonify({"error": "Invalid target_type"}), 400

    if not target_id:
        return jsonify({"error": "Invalid target_id"}), 400

    db = get_db()

    totals = db.execute(
        """
        SELECT
            SUM(CASE WHEN vote_value = 1 THEN 1 ELSE 0 END) AS likes,
            SUM(CASE WHEN vote_value = -1 THEN 1 ELSE 0 END) AS dislikes
        FROM vote
        WHERE target_type = ? AND target_id = ?
        """,
        (target_type, target_id),
    ).fetchone()

    user_vote = db.execute(
        """
        SELECT vote_value
        FROM vote
        WHERE user_id = ? AND target_type = ? AND target_id = ?
        """,
        (user_id, target_type, target_id),
    ).fetchone()

    return jsonify({
        "target_type": target_type,
        "target_id": target_id,
        "likes": totals["likes"] or 0,
        "dislikes": totals["dislikes"] or 0,
        "user_vote": user_vote["vote_value"] if user_vote else 0
        # 0 = no vote, 1 = like, -1 = dislike
    })
