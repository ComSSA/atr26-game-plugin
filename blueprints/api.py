from datetime import datetime

from flask import Blueprint, jsonify, request

from CTFd.models import db
from CTFd.utils import get_config
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

api_bp = Blueprint("atr26_game_api", __name__, url_prefix="/atr26_game/api")


def _user_mode():
    return get_config("user_mode")


def _require_account(user, team):
    if _user_mode() == "teams":
        if not team:
            return False, (jsonify({"success": False, "error": "You must be on a team"}), 403)
    return True, None


def _get_solve_for_challenge(user, team, challenge_id):
    from CTFd.models import Solves

    if _user_mode() == "teams":
        if not team:
            return None
        return Solves.query.filter_by(team_id=team.id, challenge_id=challenge_id).first()
    return Solves.query.filter_by(user_id=user.id, challenge_id=challenge_id).first()


def _card_draw_account_matches(draw, user, team):
    if _user_mode() == "teams":
        return team and draw.team_id == team.id
    return draw.user_id == user.id


def _loadout_owner_kwargs(user, team):
    if _user_mode() == "teams":
        return {"team_id": team.id, "user_id": None}
    return {"team_id": None, "user_id": user.id}


def _loadout_base_q(user, team):
    from ..models import TeamLoadout

    if _user_mode() == "teams":
        return TeamLoadout.query.filter(
            TeamLoadout.team_id == team.id,
            TeamLoadout.user_id.is_(None),
        )
    return TeamLoadout.query.filter(
        TeamLoadout.user_id == user.id,
        TeamLoadout.team_id.is_(None),
    )


def _inventory_owned_by_account(inv, user, team):
    if _user_mode() == "teams":
        return team and inv.team_id == team.id
    return inv.user_id == user.id


def _loadout_locked(user, team):
    from ..models import TeamLoadout

    q = _loadout_base_q(user, team)
    return q.filter(TeamLoadout.submitted_at.isnot(None)).first() is not None


@api_bp.route("/inventory", methods=["GET"])
@authed_only
def get_inventory():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    from ..models import TeamInventory

    if _user_mode() == "teams":
        items = TeamInventory.query.filter_by(team_id=team.id).all()
    else:
        items = TeamInventory.query.filter_by(user_id=user.id).all()
    return jsonify({"success": True, "data": [item.serialize() for item in items]})


@api_bp.route("/card-offer", methods=["GET", "POST"])
@authed_only
def card_offer():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    if request.method == "POST" and request.is_json:
        challenge_id = (request.get_json(silent=True) or {}).get("challenge_id")
    else:
        challenge_id = request.args.get("challenge_id", type=int)
    if not challenge_id:
        return jsonify({"success": False, "error": "challenge_id required"}), 400

    from ..models import CardDraw

    solve = _get_solve_for_challenge(user, team, challenge_id)
    if not solve:
        return jsonify({"success": False, "error": "No solve for this challenge"}), 404

    draw = CardDraw.query.filter_by(solve_id=solve.id).first()
    if not draw:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Loot draft not ready yet",
                    "retry": True,
                }
            ),
            409,
        )

    if not _card_draw_account_matches(draw, user, team):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    if draw.picked_slug:
        return jsonify({"success": False, "error": "Already selected a card for this solve"}), 400

    return jsonify({"success": True, "data": draw.serialize_offer()})


@api_bp.route("/card-select", methods=["POST"])
@authed_only
def card_select():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    data = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id")
    pick = (data.get("pick") or "").strip().lower()
    picked_slug = (data.get("picked_slug") or "").strip().lower()

    if not challenge_id:
        return jsonify({"success": False, "error": "challenge_id required"}), 400

    from ..models import CardDraw, TeamInventory

    solve = _get_solve_for_challenge(user, team, challenge_id)
    if not solve:
        return jsonify({"success": False, "error": "No solve for this challenge"}), 404

    draw = CardDraw.query.filter_by(solve_id=solve.id).first()
    if not draw:
        return jsonify({"success": False, "error": "No card draw for this solve"}), 404

    if not _card_draw_account_matches(draw, user, team):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    if draw.picked_slug:
        return jsonify({"success": False, "error": "Already selected"}), 400

    chosen_slug = None
    rolled = None
    if picked_slug:
        if picked_slug == (draw.weapon_slug_a or "").lower():
            chosen_slug = draw.weapon_slug_a
            rolled = draw.rolled_damage_a
        elif picked_slug == (draw.weapon_slug_b or "").lower():
            chosen_slug = draw.weapon_slug_b
            rolled = draw.rolled_damage_b
        else:
            return jsonify({"success": False, "error": "picked_slug must match one of the offered weapons"}), 400
    elif pick == "a":
        chosen_slug = draw.weapon_slug_a
        rolled = draw.rolled_damage_a
    elif pick == "b":
        chosen_slug = draw.weapon_slug_b
        rolled = draw.rolled_damage_b
    else:
        return jsonify(
            {"success": False, "error": "Provide pick ('a' or 'b') or picked_slug matching an offer"}
        ), 400

    draw.picked_slug = chosen_slug
    draw.picked_at = datetime.utcnow()

    if _user_mode() == "teams":
        inv = TeamInventory(
            team_id=team.id,
            user_id=None,
            weapon_slug=chosen_slug,
            rolled_damage=rolled,
            source_challenge_id=challenge_id,
            card_draw_id=draw.id,
        )
    else:
        inv = TeamInventory(
            team_id=None,
            user_id=user.id,
            weapon_slug=chosen_slug,
            rolled_damage=rolled,
            source_challenge_id=challenge_id,
            card_draw_id=draw.id,
        )
    db.session.add(inv)
    db.session.commit()

    return jsonify({"success": True, "data": {"message": "Card selected", "inventory_id": inv.id}})


@api_bp.route("/loadout", methods=["GET"])
@authed_only
def get_loadout():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    loadout_entries = _loadout_base_q(user, team).all()
    submitted = False
    slots = {}
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
    ok, err = _require_account(user, team)
    if not ok:
        return err

    from ..models import TeamInventory, TeamLoadout

    if _loadout_locked(user, team):
        return jsonify({"success": False, "error": "Loadout is locked after submit"}), 400

    data = request.get_json(silent=True) or {}
    slots_payload = data.get("slots")
    if not isinstance(slots_payload, dict):
        return jsonify({"success": False, "error": "slots object required"}), 400

    owner = _loadout_owner_kwargs(user, team)
    _loadout_base_q(user, team).delete(synchronize_session=False)

    seen_inv: set[int] = set()
    for slot_key, inv_id in slots_payload.items():
        try:
            slot_num = int(slot_key)
        except (TypeError, ValueError):
            continue
        if slot_num < 1 or slot_num > 5:
            return jsonify({"success": False, "error": "slot must be 1–5"}), 400
        try:
            inv_pk = int(inv_id)
        except (TypeError, ValueError):
            continue
        if inv_pk in seen_inv:
            return jsonify({"success": False, "error": "same weapon cannot fill two slots"}), 400
        seen_inv.add(inv_pk)

        inv = TeamInventory.query.filter_by(id=inv_pk).first()
        if not inv or not _inventory_owned_by_account(inv, user, team):
            db.session.rollback()
            return jsonify({"success": False, "error": f"invalid inventory id {inv_pk}"}), 400

        db.session.add(
            TeamLoadout(
                slot_number=slot_num,
                inventory_id=inv_pk,
                submitted_at=None,
                **owner,
            )
        )

    db.session.commit()
    return jsonify({"success": True, "data": {"message": "Loadout saved"}})


@api_bp.route("/loadout/submit", methods=["POST"])
@authed_only
def submit_loadout():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    if _loadout_locked(user, team):
        return jsonify({"success": False, "error": "Loadout already submitted"}), 400

    rows = _loadout_base_q(user, team).all()
    if not rows:
        return jsonify({"success": False, "error": "Save a loadout before submitting"}), 400

    now = datetime.utcnow()
    for row in rows:
        row.submitted_at = now
    db.session.commit()
    return jsonify({"success": True, "data": {"message": "Loadout submitted"}})


@api_bp.route("/hints", methods=["GET"])
@authed_only
def get_hints():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    from ..models import TeamHint

    if team:
        hints = TeamHint.query.filter_by(team_id=team.id).all()
    else:
        hints = []
    return jsonify({"success": True, "data": [hint.serialize() for hint in hints]})


@api_bp.route("/battle/results", methods=["GET"])
@authed_only
def get_battle_results():
    user = get_current_user()
    team = user.team
    ok, err = _require_account(user, team)
    if not ok:
        return err

    from ..models import BattleResult

    if not team:
        return jsonify({"success": True, "data": None})
    result = BattleResult.query.filter_by(team_id=team.id).first()
    if not result:
        return jsonify({"success": True, "data": None})

    return jsonify({"success": True, "data": result.serialize()})
