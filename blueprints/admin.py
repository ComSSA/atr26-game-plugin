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
    loot_entries = LootTable.query.all()
    return render_template(
        "admin_weapons.html",
        weapons=weapons,
        loot_entries=loot_entries,
    )


@admin_bp.route("/weapons", methods=["POST"])
@admins_only
def create_weapon():
    from ..models import Weapon

    weapon = Weapon(
        name=request.form.get("name", "Unnamed Weapon"),
        description=request.form.get("description", ""),
        rarity=request.form.get("rarity", "common"),
        damage_type=request.form.get("damage_type", "physical"),
        icon_path=request.form.get("icon_path", ""),
        card_border_color=request.form.get("card_border_color", "#808080"),
        base_damage=int(request.form.get("base_damage", 0)),
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
    weapon.base_damage = int(request.form.get("base_damage", weapon.base_damage))
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
