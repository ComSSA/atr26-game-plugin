import random
from datetime import datetime

from flask import Blueprint, jsonify, request

from CTFd.models import db
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

    from ..models import LootTable, PendingCardOffer

    existing = PendingCardOffer.query.filter_by(
        team_id=team.id, challenge_id=challenge_id
    ).first()

    if existing and not existing.selected:
        return jsonify({"success": True, "data": existing.serialize()})

    if existing and existing.selected:
        return jsonify({"success": False, "error": "Already selected a card for this challenge"}), 400

    entries = LootTable.query.filter_by(challenge_id=challenge_id).all()
    if not entries:
        return jsonify({"success": False, "error": "No loot configured for this challenge"}), 404

    weights = [e.weight for e in entries]

    if len(entries) == 1:
        entry_a = entry_b = entries[0]
    else:
        idx_a = random.choices(range(len(entries)), weights=weights)[0]
        remaining = [(e, w) for i, (e, w) in enumerate(zip(entries, weights)) if i != idx_a]
        rem_weights = [r[1] for r in remaining]
        idx_b = random.choices(range(len(remaining)), weights=rem_weights)[0]
        entry_a = entries[idx_a]
        entry_b = remaining[idx_b][0]

    offer = PendingCardOffer(
        team_id=team.id,
        challenge_id=challenge_id,
        weapon_id_a=entry_a.weapon_id,
        weapon_id_b=entry_b.weapon_id,
    )
    db.session.add(offer)
    db.session.commit()
    return jsonify({"success": True, "data": offer.serialize()})


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

    from ..models import PendingCardOffer, TeamHint, TeamInventory

    offer = PendingCardOffer.query.filter_by(id=offer_id, team_id=team.id).first()
    if not offer:
        return jsonify({"success": False, "error": "Offer not found"}), 404

    if offer.selected:
        return jsonify({"success": False, "error": "Already selected"}), 400

    if selected_weapon_id not in (offer.weapon_id_a, offer.weapon_id_b):
        return jsonify({"success": False, "error": "Invalid weapon selection"}), 400

    offer.selected = True

    lo = selected_weapon.min_damage or 0
    hi = selected_weapon.max_damage or 0
    rolled = random.randint(min(lo, hi), max(lo, hi)) if hi > lo else lo

    inv = TeamInventory(
        team_id=team.id,
        weapon_id=selected_weapon_id,
        source_challenge_id=offer.challenge_id,
        rolled_damage=rolled,
    )
    db.session.add(inv)

    selected_weapon = (
        offer.weapon_a if selected_weapon_id == offer.weapon_id_a else offer.weapon_b
    )

    hint = None
    if selected_weapon.hint_text:
        hint = TeamHint(
            team_id=team.id,
            source_challenge_id=offer.challenge_id,
            hint_content=selected_weapon.hint_text,
        )
        db.session.add(hint)

    db.session.commit()

    response_data = {"weapon": selected_weapon.serialize()}
    if hint:
        response_data["hint"] = hint.serialize()

    return jsonify({"success": True, "data": response_data})


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

    from ..models import TeamInventory, TeamLoadout

    existing = TeamLoadout.query.filter_by(team_id=team.id).first()
    if existing and existing.submitted_at:
        return jsonify({"success": False, "error": "Loadout already submitted"}), 400

    data = request.get_json()
    slots = data.get("slots", {})

    TeamLoadout.query.filter_by(team_id=team.id).delete()

    for slot_str, inv_id in slots.items():
        slot_num = int(slot_str)
        if slot_num < 1 or slot_num > 5:
            continue
        inv = TeamInventory.query.filter_by(id=inv_id, team_id=team.id).first()
        if not inv:
            continue
        db.session.add(TeamLoadout(
            team_id=team.id,
            slot_number=slot_num,
            inventory_id=inv_id,
        ))

    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/loadout/submit", methods=["POST"])
@authed_only
def submit_loadout():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from ..models import TeamLoadout

    entries = TeamLoadout.query.filter_by(team_id=team.id).all()
    if not entries:
        return jsonify({"success": False, "error": "No loadout to submit"}), 400

    if any(e.submitted_at for e in entries):
        return jsonify({"success": False, "error": "Loadout already submitted"}), 400

    now = datetime.utcnow()
    for entry in entries:
        entry.submitted_at = now
    db.session.commit()
    return jsonify({"success": True})


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
