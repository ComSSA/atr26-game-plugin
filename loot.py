"""
Loot RNG: tier tags set per-card *rarity* rolls, then a random weapon in that rarity bucket.
Rolled damage still uses each weapon's catalog rarity. (Weighted pick across all weapons skews
heavily toward rare tiers when the catalog is tiny — e.g. one legendary in four weapons.)
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from CTFd.models import Solves

# Inclusive damage ranges by catalog rarity (rolled per card at drop time).
DAMAGE_RANGE = {
    "common": (25, 30),
    "uncommon": (30, 35),
    "rare": (35, 40),
    "legendary": (40, 50),
}

# Per-card rarity roll weights by challenge loot tier (must sum > 0).
# Easy: no legendary on the rarity roll (still get rares). Medium: low legendary; hard: real jackpot.
# For easy/medium, the second card never rolls legendary if the first card is already legendary
# (avoids “double orange” drafts that feel rigged with small catalogs).
LOOT_TIER_WEIGHTS = {
    "easy": {"common": 55, "uncommon": 33, "rare": 12, "legendary": 0},
    "medium": {"common": 36, "uncommon": 36, "rare": 24, "legendary": 4},
    "hard": {"common": 18, "uncommon": 24, "rare": 38, "legendary": 20},
}


def normalize_rarity_for_damage(rarity: str) -> str:
    r = (rarity or "common").strip().lower()
    if r == "epic":
        return "rare"
    if r in DAMAGE_RANGE:
        return r
    return "common"


def normalize_rarity_for_weight(rarity: str) -> str:
    r = (rarity or "common").strip().lower()
    if r == "epic":
        return "rare"
    if r in LOOT_TIER_WEIGHTS["easy"]:
        return r
    return "common"


def roll_damage_for_rarity(rarity: str) -> int:
    key = normalize_rarity_for_damage(rarity)
    lo, hi = DAMAGE_RANGE[key]
    return random.randint(lo, hi)


def loot_tier_from_tag_values(values: list[str]) -> Optional[str]:
    s = {v.strip().lower() for v in values if v}
    if "loot:off" in s:
        return None
    if "loot:hard" in s:
        return "hard"
    if "loot:medium" in s:
        return "medium"
    if "loot:easy" in s:
        return "easy"
    return None


def _roll_rarity_for_tier(tier: str, *, exclude_legendary: bool = False) -> str:
    table = dict(LOOT_TIER_WEIGHTS.get(tier, LOOT_TIER_WEIGHTS["medium"]))
    if exclude_legendary:
        table["legendary"] = 0
    rarities = list(table.keys())
    weights = [max(0, int(table[r])) for r in rarities]
    if sum(weights) <= 0:
        return "common"
    return random.choices(rarities, weights=weights, k=1)[0]


def _weapons_by_rarity(weapons: list) -> dict[str, list]:
    d: dict[str, list] = defaultdict(list)
    for w in weapons:
        d[normalize_rarity_for_weight(w.rarity)].append(w)
    return d


def _pick_weapon_from_bucket(bucket: list, exclude_slugs: set[str]):
    pool = [w for w in bucket if w.slug not in exclude_slugs]
    if not pool:
        return None
    return random.choice(pool)


def _eligible_pool(weapons: list, exclude: set[str], tier: str, allow_legendary: Optional[bool] = None):
    """Weapons not in exclude; easy tier never includes legendary unless allow_legendary is True."""
    if allow_legendary is None:
        allow_legendary = tier != "easy"
    out = []
    for w in weapons:
        if w.slug in exclude:
            continue
        if not allow_legendary and normalize_rarity_for_weight(w.rarity) == "legendary":
            continue
        out.append(w)
    return out


def _fallback_pick(weapons: list, exclude: set[str], tier: str):
    pool = _eligible_pool(weapons, exclude, tier, allow_legendary=False)
    if pool:
        return random.choice(pool)
    pool = [w for w in weapons if w.slug not in exclude]
    return random.choice(pool) if pool else None


def _pick_two_weapons(weapons: list, tier: str):
    """Roll rarity per offer slot, then uniform weapon within that bucket; fallback if bucket empty."""
    if not weapons:
        return None, None
    if len(weapons) == 1:
        return weapons[0], weapons[0]

    by_r = _weapons_by_rarity(weapons)
    exclude: set[str] = set()

    ra = _roll_rarity_for_tier(tier)
    wa = _pick_weapon_from_bucket(by_r.get(ra, []), exclude)
    if wa is None:
        wa = _fallback_pick(weapons, exclude, tier)
        if wa is None:
            return None, None
    exclude.add(wa.slug)

    first_is_leg = normalize_rarity_for_weight(wa.rarity) == "legendary"
    no_double_leg = tier in ("easy", "medium") and first_is_leg
    rb = _roll_rarity_for_tier(tier, exclude_legendary=no_double_leg)
    wb = _pick_weapon_from_bucket(by_r.get(rb, []), exclude)
    if wb is None:
        wb = _fallback_pick(weapons, exclude, tier)
        if wb is None:
            wb = wa
    if wb.slug == wa.slug:
        rest = _eligible_pool(weapons, {wa.slug}, tier, allow_legendary=tier != "easy")
        if not rest:
            rest = [w for w in weapons if w.slug != wa.slug]
        wb = random.choice(rest) if rest else wa
    return wa, wb


def roll_card_draw_for_solve(solve: "Solves"):
    """
    Build a CardDraw for this solve if the challenge is loot-tagged and the catalog has weapons.
    Caller adds the returned object to the session. Returns None if no drop.
    """
    from CTFd.models import Tags

    from .models import CardDraw, Weapon

    tags = Tags.query.filter_by(challenge_id=solve.challenge_id).all()
    values = [t.value for t in tags]
    tier = loot_tier_from_tag_values(values)
    if tier is None:
        return None

    weapons = Weapon.query.filter_by(enabled=True).all()
    if not weapons:
        return None

    wa, wb = _pick_two_weapons(weapons, tier)
    if wa is None:
        return None

    return CardDraw(
        solve_id=solve.id,
        team_id=solve.team_id,
        user_id=solve.user_id,
        challenge_id=solve.challenge_id,
        weapon_slug_a=wa.slug,
        weapon_slug_b=wb.slug,
        rolled_damage_a=roll_damage_for_rarity(wa.rarity),
        rolled_damage_b=roll_damage_for_rarity(wb.rarity),
    )
