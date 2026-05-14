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


def _plugin_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@admin_bp.route("/weapons", methods=["GET"])
@admins_only
def weapons_page():
    from ..models import Weapon

    weapons = Weapon.query.order_by(Weapon.slug.asc()).all()
    return render_template(
        "admin_weapons.html",
        weapons=weapons,
    )


@admin_bp.route("/weapons", methods=["POST"])
@admins_only
def create_weapon():
    from ..models import Weapon

    slug = (request.form.get("slug") or "").strip().lower()
    if not slug:
        return jsonify({"success": False, "error": "slug required"}), 400

    weapon = Weapon(
        slug=slug,
        name=request.form.get("name", "Unnamed Weapon"),
        description=request.form.get("description", ""),
        rarity=request.form.get("rarity", "common"),
        damage_type=request.form.get("damage_type", "physical"),
        icon_path=request.form.get("icon_path", ""),
        card_border_color=request.form.get("card_border_color", "#808080"),
        enabled=request.form.get("enabled", "1") == "1",
    )
    db.session.add(weapon)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Could not create weapon (duplicate slug?)"}), 400
    return jsonify({"success": True, "data": weapon.serialize()})


@admin_bp.route("/weapons/<int:weapon_id>/update", methods=["POST"])
@admins_only
def update_weapon(weapon_id):
    from ..models import Weapon

    weapon = Weapon.query.filter_by(id=weapon_id).first_or_404()
    new_slug = request.form.get("slug")
    if new_slug:
        weapon.slug = new_slug.strip().lower()
    weapon.name = request.form.get("name", weapon.name)
    weapon.description = request.form.get("description", weapon.description)
    weapon.rarity = request.form.get("rarity", weapon.rarity)
    weapon.damage_type = request.form.get("damage_type", weapon.damage_type)
    weapon.icon_path = request.form.get("icon_path", weapon.icon_path)
    weapon.card_border_color = request.form.get("card_border_color", weapon.card_border_color)
    if request.form.get("enabled") is not None:
        weapon.enabled = request.form.get("enabled") == "1"
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Update failed"}), 400
    return jsonify({"success": True, "data": weapon.serialize()})


@admin_bp.route("/weapons/<int:weapon_id>/delete", methods=["POST"])
@admins_only
def delete_weapon(weapon_id):
    from ..models import Weapon

    weapon = Weapon.query.filter_by(id=weapon_id).first_or_404()
    db.session.delete(weapon)
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/weapons/seed", methods=["POST"])
@admins_only
def seed_weapons():
    from ..seed import upsert_weapons_from_records

    records = None
    if request.is_json:
        body = request.get_json(silent=True)
        if isinstance(body, list):
            records = body
        elif isinstance(body, dict) and "weapons" in body:
            records = body["weapons"]
    if records is None:
        path = request.args.get("path") or os.path.join(_plugin_root(), "weapons_seed.json")
        if not os.path.isfile(path):
            return jsonify({"success": False, "error": f"Seed file not found: {path}"}), 400
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "weapons" in data:
            records = data["weapons"]
        elif isinstance(data, list):
            records = data
        else:
            return jsonify({"success": False, "error": "Invalid seed JSON shape"}), 400

    created, updated = upsert_weapons_from_records(records)
    return jsonify({"success": True, "data": {"created": created, "updated": updated}})


@admin_bp.route("/test-challenges/seed", methods=["POST"])
@admins_only
def seed_test_challenges_route():
    from ..seed_challenges import seed_test_challenges

    created, skipped = seed_test_challenges()
    return jsonify({"success": True, "data": {"created": created, "skipped": skipped}})


@admin_bp.route("/teams", methods=["GET"])
@admins_only
def teams_page():
    from CTFd.models import Teams

    from ..models import BattleResult, TeamInventory, TeamLoadout

    teams = Teams.query.all()
    team_data = []
    for team in teams:
        inv_count = TeamInventory.query.filter_by(team_id=team.id).count()
        loadout_submitted = (
            TeamLoadout.query.filter_by(team_id=team.id)
            .filter(TeamLoadout.submitted_at.isnot(None))
            .first()
            is not None
        )
        battle = BattleResult.query.filter_by(team_id=team.id).first()
        team_data.append({
            "team": team,
            "inventory_count": inv_count,
            "loadout_submitted": loadout_submitted,
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
