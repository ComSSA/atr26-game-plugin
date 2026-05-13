from flask import Blueprint, jsonify, request

from CTFd.utils.decorators import authed_only

loot_bp = Blueprint("loot_frontend", __name__, url_prefix="/api/v1/loot")


@loot_bp.route("/claim", methods=["POST"])
@authed_only
def claim():
    data = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    item_id = data.get("item_id")
    # Stub: accept the claim and return success.
    # Wire up real loot award logic here once the loot pool source is integrated.
    return jsonify(
        {"success": True, "data": {"challenge_id": challenge_id, "item_id": item_id}}
    )
