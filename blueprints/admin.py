import json
import os

from flask import Blueprint, jsonify, render_template, request

from CTFd.models import db
from CTFd.utils.decorators import admins_only

admin_bp = Blueprint(
    "atr26_game_admin",
    __name__,
    template_folder="../templates",
    url_prefix="/atr26_game/admin",
)


@admin_bp.route("/weapons", methods=["GET"])
@admins_only
def weapons_page():
    from ..models import LootTable, Weapon

    weapons = Weapon.query.all()
    return render_template("admin_weapons.html", weapons=weapons)


@admin_bp.route("/weapons", methods=["POST"])
@admins_only
def create_weapon():
    from ..models import Weapon

    weapon = Weapon(
        name=request.form.get("name", "Unnamed Weapon"),
        description=request.form.get("description", ""),
        rarity=request.form.get("rarity", "common"),
        damage_type=request.form.get("damage_type", "fire"),
        icon_path=request.form.get("icon_path", ""),
        card_border_color=request.form.get("card_border_color", "#808080"),
        min_damage=int(request.form.get("min_damage", 0)),
        max_damage=int(request.form.get("max_damage", 0)),
        hint_text=request.form.get("hint_text", ""),
    )
    db.session.add(weapon)
    db.session.commit()
    return jsonify({"success": True, "data": weapon.serialize()})


@admin_bp.route("/weapons/<int:weapon_id>/update", methods=["POST"])
@admins_only
def update_weapon(weapon_id):
    from ..models import Weapon

    weapon = Weapon.query.filter_by(id=weapon_id).first_or_404()
    weapon.name = request.form.get("name", weapon.name)
    weapon.description = request.form.get("description", weapon.description)
    weapon.rarity = request.form.get("rarity", weapon.rarity)
    weapon.damage_type = request.form.get("damage_type", weapon.damage_type)
    weapon.icon_path = request.form.get("icon_path", weapon.icon_path)
    weapon.card_border_color = request.form.get("card_border_color", weapon.card_border_color)
    weapon.min_damage = int(request.form.get("min_damage", weapon.min_damage))
    weapon.max_damage = int(request.form.get("max_damage", weapon.max_damage))
    weapon.hint_text = request.form.get("hint_text", weapon.hint_text)
    db.session.commit()
    return jsonify({"success": True, "data": weapon.serialize()})


@admin_bp.route("/weapons/<int:weapon_id>/delete", methods=["POST"])
@admins_only
def delete_weapon(weapon_id):
    from ..models import Weapon

    weapon = Weapon.query.filter_by(id=weapon_id).first_or_404()
    db.session.delete(weapon)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/loot-table", methods=["POST"])
@admins_only
def add_loot_entry():
    from ..models import LootTable

    entry = LootTable(
        challenge_id=int(request.form.get("challenge_id")),
        weapon_id=int(request.form.get("weapon_id")),
        weight=int(request.form.get("weight", 1)),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"success": True, "data": entry.serialize()})


@admin_bp.route("/loot-table/<int:entry_id>/delete", methods=["POST"])
@admins_only
def delete_loot_entry(entry_id):
    from ..models import LootTable

    entry = LootTable.query.filter_by(id=entry_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/teams", methods=["GET"])
@admins_only
def teams_page():
    from CTFd.models import Teams

    from ..models import BattleResult, TeamInventory, TeamLoadout

    teams = Teams.query.all()
    team_data = []
    for team in teams:
        inv_count = TeamInventory.query.filter_by(team_id=team.id).count()
        loadout = TeamLoadout.query.filter_by(team_id=team.id).first()
        battle = BattleResult.query.filter_by(team_id=team.id).first()
        team_data.append({
            "team": team,
            "inventory_count": inv_count,
            "loadout_submitted": loadout.submitted_at is not None if loadout else False,
            "battle_result": battle,
        })
    return render_template("admin_teams.html", team_data=team_data)


@admin_bp.route("/battle", methods=["GET"])
@admins_only
def battle_page():
    from ..models import BattleResult

    results = BattleResult.query.all()
    return render_template("admin_battle.html", results=results)


@admin_bp.route("/battle/run", methods=["POST"])
@admins_only
def run_battle():
    # TODO: Implement auto-battler logic
    return jsonify({"success": True, "data": {"message": "Battle simulation (stub)"}})


@admin_bp.route("/catalog/seed-weapons", methods=["POST"])
@admins_only
def seed_weapons():
    seed_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "weapons_seed.json")
    if not os.path.exists(seed_file):
        return jsonify({"success": False, "error": "weapons_seed.json not found in plugin root"}), 404

    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)

    from ..models import Weapon

    created = updated = 0
    for entry in data:
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        existing = Weapon.query.filter_by(name=name).first()
        if existing:
            for field in ("description", "rarity", "damage_type", "icon_path",
                          "card_border_color", "min_damage", "max_damage", "hint_text"):
                if field in entry:
                    setattr(existing, field, entry[field])
            updated += 1
        else:
            db.session.add(Weapon(
                name=name,
                description=entry.get("description", ""),
                rarity=entry.get("rarity", "common"),
                damage_type=entry.get("damage_type", "fire"),
                icon_path=entry.get("icon_path", ""),
                card_border_color=entry.get("card_border_color", "#808080"),
                min_damage=int(entry.get("min_damage", 0)),
                max_damage=int(entry.get("max_damage", 0)),
                hint_text=entry.get("hint_text", ""),
            ))
            created += 1

    db.session.commit()
    return jsonify({"success": True, "data": {"created": created, "updated": updated}})


_SEED_CHALLENGES = [
    {"name": "ATR26 — Warmup I",    "description": "Get started.\n\nFlag: `ATR26{warm_up_one}`",   "value": 50,  "tier": "easy"},
    {"name": "ATR26 — Warmup II",   "description": "Keep going.\n\nFlag: `ATR26{warm_up_two}`",    "value": 75,  "tier": "easy"},
    {"name": "ATR26 — Challenge I", "description": "Think harder.\n\nFlag: `ATR26{mid_tier_one}`", "value": 150, "tier": "medium"},
    {"name": "ATR26 — Challenge II","description": "Almost there.\n\nFlag: `ATR26{mid_tier_two}`", "value": 200, "tier": "medium"},
    {"name": "ATR26 — Endgame I",   "description": "Prove yourself.\n\nFlag: `ATR26{end_one}`",    "value": 400, "tier": "hard"},
    {"name": "ATR26 — Endgame II",  "description": "True challenge.\n\nFlag: `ATR26{end_two}`",    "value": 500, "tier": "hard"},
]


@admin_bp.route("/catalog/seed-challenges", methods=["POST"])
@admins_only
def seed_challenges():
    from CTFd.models import Challenges as CTFdChallenges, Tags

    created = skipped = 0
    for entry in _SEED_CHALLENGES:
        if CTFdChallenges.query.filter_by(name=entry["name"]).first():
            skipped += 1
            continue
        c = CTFdChallenges(
            name=entry["name"],
            description=entry["description"],
            value=entry["value"],
            category="ATR26",
            type="standard",
            state="visible",
        )
        db.session.add(c)
        db.session.flush()
        db.session.add(Tags(challenge_id=c.id, value=f"loot:{entry['tier']}"))
        created += 1

    db.session.commit()
    return jsonify({"success": True, "data": {"created": created, "skipped": skipped}})
