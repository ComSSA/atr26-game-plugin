from datetime import datetime

from flask import Blueprint, jsonify, request

from CTFd.models import db
from CTFd.utils import get_config
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

api_bp = Blueprint("atr26_game_api", __name__, url_prefix="/atr26_game/api")

LOOT_TIER_WEIGHTS = {
    "easy":   {"common": 48, "uncommon": 32, "rare": 14, "legendary": 6},
    "medium": {"common": 28, "uncommon": 32, "rare": 28, "legendary": 12},
    "hard":   {"common": 12, "uncommon": 22, "rare": 33, "legendary": 33},
}


def _challenge_tier(challenge, tag_values=None):
    """Return the loot tier string, or None if loot:off is set."""
    if tag_values is None:
        from CTFd.models import Tags
        tag_values = (
            {t.value.lower() for t in Tags.query.filter_by(challenge_id=challenge.id).all()}
            if challenge else set()
        )
    if "loot:off" in tag_values:
        return None
    for tag in tag_values:
        if tag.startswith("loot:") and tag[5:] in LOOT_TIER_WEIGHTS:
            return tag[5:]
    if challenge is None:
        return "medium"
    cat = (challenge.category or "").strip().lower()
    if cat in LOOT_TIER_WEIGHTS:
        return cat
    v = challenge.value or 0
    if v <= 100:
        return "easy"
    if v <= 300:
        return "medium"
    return "hard"


def _pick_by_rarity(weapons, tier):
    """Roll rarity first, then pick a random weapon of that rarity.

    Constraints:
      easy   — legendary never appears
      medium — both cards cannot be legendary simultaneously
      hard   — no restrictions
    """
    tier_w = LOOT_TIER_WEIGHTS[tier]

    by_rarity = {}
    for w in weapons:
        r = (w.rarity or "common").lower()
        by_rarity.setdefault(r, []).append(w)

    rarities = list(tier_w.keys())
    if tier == "easy":
        rarities = [r for r in rarities if r != "legendary"]

    available = [(r, tier_w[r]) for r in rarities if by_rarity.get(r)]
    if not available:
        return None, None

    a_rarities, a_weights = zip(*available)
    rarity_a = random.choices(list(a_rarities), weights=list(a_weights))[0]
    weapon_a = random.choice(by_rarity[rarity_a])

    b_pool = list(available)
    if tier == "medium" and rarity_a == "legendary":
        b_pool = [(r, w) for r, w in b_pool if r != "legendary"]
    if not b_pool:
        b_pool = list(available)

    b_rarities, b_weights = zip(*b_pool)
    rarity_b = random.choices(list(b_rarities), weights=list(b_weights))[0]

    def _different(w):
        if w.id == weapon_a.id:
            return False
        same_concept = (
            (w.name or "").strip().lower() == (weapon_a.name or "").strip().lower()
            and (w.damage_type or "").lower() == (weapon_a.damage_type or "").lower()
            and (w.rarity or "").lower() == (weapon_a.rarity or "").lower()
        )
        return not same_concept

    candidates = [w for w in by_rarity[rarity_b] if _different(w)]
    # Fallback: relax to just different ID if no conceptually distinct weapon exists
    if not candidates:
        candidates = [w for w in by_rarity[rarity_b] if w.id != weapon_a.id]
    weapon_b = random.choice(candidates if candidates else by_rarity[rarity_b])

    return weapon_a, weapon_b


@api_bp.route("/pending-offers", methods=["GET"])
@authed_only
def get_pending_offers():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from ..models import PendingCardOffer

    offers = (
        PendingCardOffer.query
        .filter_by(team_id=team.id, selected=False)
        .order_by(PendingCardOffer.created_at.asc())
        .all()
    )
    return jsonify({"success": True, "data": [o.serialize() for o in offers]})


@api_bp.route("/activity-summary", methods=["GET"])
@authed_only
def activity_summary():
    user = get_current_user()
    team = user.team
    if not team:
        return jsonify({"success": False, "error": "You must be on a team"}), 403

    from CTFd.models import Challenges as CTFdChallenges
    from ..models import PendingCardOffer

    offers = (
        PendingCardOffer.query
        .filter_by(team_id=team.id)
        .order_by(PendingCardOffer.created_at.desc())
        .all()
    )

    result = []
    for offer in offers:
        challenge = CTFdChallenges.query.get(offer.challenge_id)
        result.append({
            "offer": offer.serialize(),
            "challenge_name": challenge.name if challenge else f"Challenge #{offer.challenge_id}",
        })

    return jsonify({"success": True, "data": result})


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

    from CTFd.models import Challenges as CTFdChallenges, Tags
    from ..models import LootTable, PendingCardOffer, Weapon

    existing = PendingCardOffer.query.filter_by(
        team_id=team.id, challenge_id=challenge_id
    ).first()

    if not _card_draw_account_matches(draw, user, team):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    if draw.picked_slug:
        return jsonify({"success": False, "error": "Already selected a card for this solve"}), 400

    challenge_obj = CTFdChallenges.query.get(challenge_id)
    tag_values = {t.value.lower() for t in Tags.query.filter_by(challenge_id=challenge_id).all()}

    tier = _challenge_tier(challenge_obj, tag_values)
    if tier is None:
        return jsonify({"success": False, "error": "Loot disabled for this challenge"})

    # Challenge-specific loot table takes priority over the global pool
    entries = LootTable.query.filter_by(challenge_id=challenge_id).all()
    if entries:
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

    # Global rarity-first pool
    weapons = Weapon.query.all()
    if not weapons:
        return jsonify({"success": False, "error": "No weapons have been configured yet"})

    weapon_a, weapon_b = _pick_by_rarity(weapons, tier)
    if weapon_a is None:
        return jsonify({"success": False, "error": "No weapons available for this tier"}), 500

    offer = PendingCardOffer(
        team_id=team.id,
        challenge_id=challenge_id,
        weapon_id_a=weapon_a.id,
        weapon_id_b=weapon_b.id,
    )
    db.session.add(offer)
    db.session.commit()
    return jsonify({"success": True, "data": offer.serialize()})


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

    selected_weapon = (
        offer.weapon_a if selected_weapon_id == offer.weapon_id_a else offer.weapon_b
    )

    RARITY_DAMAGE = {"common": (10, 20), "uncommon": (20, 30), "rare": (30, 40), "legendary": (40, 50)}
    lo, hi = RARITY_DAMAGE.get((selected_weapon.rarity or "common").lower(), (10, 20))
    rolled = random.randint(lo, hi)

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

    hint = None
    if selected_weapon.hint_text:
        hint = TeamHint(
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
