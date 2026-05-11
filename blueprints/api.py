from flask import Blueprint, jsonify, request

from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

api_bp = Blueprint("atr26_game_api", __name__, url_prefix="/atr26_game/api")


@api_bp.route("/inventory", methods=["GET"])
@authed_only
def get_inventory():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from ..models import TeamInventory

    items = TeamInventory.query.filter_by(team_id=team.id).all()
    return jsonify({"success": True, "data": [item.serialize() for item in items]})


@api_bp.route("/card-offer", methods=["POST"])
@authed_only
def card_offer():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    data = request.get_json()
    challenge_id = data.get("challenge_id")
    if not challenge_id:
        return jsonify({"success": False, "error": "challenge_id required"}), 400

    from ..models import PendingCardOffer

    existing = PendingCardOffer.query.filter_by(
        team_id=team.id, challenge_id=challenge_id
    ).first()

    if existing and not existing.selected:
        return jsonify({"success": True, "data": existing.serialize()})

    if existing and existing.selected:
        return jsonify({"success": False, "error": "Already selected a card for this challenge"}), 400

    # TODO: Roll two weapons from loot table using weighted random selection
    # For now, return a placeholder
    return jsonify({"success": False, "error": "No loot table configured for this challenge"}), 404


@api_bp.route("/card-select", methods=["POST"])
@authed_only
def card_select():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    data = request.get_json()
    offer_id = data.get("offer_id")
    selected_weapon_id = data.get("selected_weapon_id")

    if not offer_id or not selected_weapon_id:
        return jsonify({"success": False, "error": "offer_id and selected_weapon_id required"}), 400

    from ..models import PendingCardOffer

    offer = PendingCardOffer.query.filter_by(id=offer_id, team_id=team.id).first()
    if not offer:
        return jsonify({"success": False, "error": "Offer not found"}), 404

    if offer.selected:
        return jsonify({"success": False, "error": "Already selected"}), 400

    if selected_weapon_id not in (offer.weapon_id_a, offer.weapon_id_b):
        return jsonify({"success": False, "error": "Invalid weapon selection"}), 400

    # TODO: Create TeamInventory entry, mark offer as selected, create TeamHint if applicable
    return jsonify({"success": True, "data": {"message": "Card selected (stub)"}})


@api_bp.route("/loadout", methods=["GET"])
@authed_only
def get_loadout():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from ..models import TeamLoadout

    slots = {}
    loadout_entries = TeamLoadout.query.filter_by(team_id=team.id).all()
    submitted = False
    for entry in loadout_entries:
        slots[entry.slot_number] = entry.serialize()
        if entry.submitted_at:
            submitted = True

    return jsonify({"success": True, "data": {"slots": slots, "submitted": submitted}})


@api_bp.route("/loadout", methods=["POST"])
@authed_only
def save_loadout():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    # TODO: Validate slot assignments, upsert TeamLoadout rows
    return jsonify({"success": True, "data": {"message": "Loadout saved (stub)"}})


@api_bp.route("/loadout/submit", methods=["POST"])
@authed_only
def submit_loadout():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    # TODO: Lock in loadout by setting submitted_at on all entries
    return jsonify({"success": True, "data": {"message": "Loadout submitted (stub)"}})


@api_bp.route("/hints", methods=["GET"])
@authed_only
def get_hints():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from ..models import TeamHint

    hints = TeamHint.query.filter_by(team_id=team.id).all()
    return jsonify({"success": True, "data": [hint.serialize() for hint in hints]})


@api_bp.route("/battle/results", methods=["GET"])
@authed_only
def get_battle_results():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from ..models import BattleResult

    result = BattleResult.query.filter_by(team_id=team.id).first()
    if not result:
        return jsonify({"success": True, "data": None})

    return jsonify({"success": True, "data": result.serialize()})
