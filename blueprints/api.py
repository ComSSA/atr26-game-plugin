import random
from datetime import datetime

from flask import Blueprint, jsonify, request

from CTFd.models import db
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

    from CTFd.models import Challenges as CTFdChallenges, Tags
    from ..models import LootTable, PendingCardOffer, Weapon

    existing = PendingCardOffer.query.filter_by(
        team_id=team.id, challenge_id=challenge_id
    ).first()

    if existing and not existing.selected:
        return jsonify({"success": True, "data": existing.serialize()})

    if existing and existing.selected:
        return jsonify({"success": False, "error": "Already selected a card for this challenge"}), 400

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

    selected_weapon = (
        offer.weapon_a if selected_weapon_id == offer.weapon_id_a else offer.weapon_b
    )

    RARITY_DAMAGE = {"common": (10, 20), "uncommon": (20, 30), "rare": (30, 40), "legendary": (40, 50)}
    lo, hi = RARITY_DAMAGE.get((selected_weapon.rarity or "common").lower(), (10, 20))
    rolled = random.randint(lo, hi)

    inv = TeamInventory(
        team_id=team.id,
        weapon_id=selected_weapon_id,
        source_challenge_id=offer.challenge_id,
        rolled_damage=rolled,
    )
    db.session.add(inv)

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
