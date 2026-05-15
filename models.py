from datetime import datetime

from sqlalchemy.orm import relationship

from CTFd.models import db


class Weapon(db.Model):
    __tablename__ = "atr26_weapons"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default="")
    rarity = db.Column(db.String(32), nullable=False, default="common")
    damage_type = db.Column(db.String(64), nullable=False, default="physical")
    icon_path = db.Column(db.Text, default="")
    card_border_color = db.Column(db.String(7), default="#808080")
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    def serialize(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "rarity": self.rarity,
            "damage_type": self.damage_type,
            "icon_path": self.icon_path,
            "icon": self.icon_path,
            "card_border_color": self.card_border_color,
            "enabled": self.enabled,
        }


class CardDraw(db.Model):
    __tablename__ = "atr26_card_draws"
    __table_args__ = (db.UniqueConstraint("solve_id", name="uq_card_draw_solve"),)

    id = db.Column(db.Integer, primary_key=True)
    solve_id = db.Column(
        db.Integer, db.ForeignKey("solves.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    weapon_slug_a = db.Column(
        db.String(80), db.ForeignKey("atr26_weapons.slug", ondelete="CASCADE"), nullable=False
    )
    weapon_slug_b = db.Column(
        db.String(80), db.ForeignKey("atr26_weapons.slug", ondelete="CASCADE"), nullable=False
    )
    rolled_damage_a = db.Column(db.Integer, nullable=False)
    rolled_damage_b = db.Column(db.Integer, nullable=False)
    picked_slug = db.Column(db.String(80), nullable=True)
    picked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    solve = relationship("Solves", foreign_keys=[solve_id])

    def serialize_offer(self):
        wa = Weapon.query.filter_by(slug=self.weapon_slug_a).first()
        wb = Weapon.query.filter_by(slug=self.weapon_slug_b).first()
        out = {
            "id": self.id,
            "solve_id": self.solve_id,
            "challenge_id": self.challenge_id,
            "picked_slug": self.picked_slug,
            "weapon_a": None,
            "weapon_b": None,
        }
        if wa:
            d = wa.serialize()
            d["rolled_damage"] = self.rolled_damage_a
            out["weapon_a"] = d
        if wb:
            d = wb.serialize()
            d["rolled_damage"] = self.rolled_damage_b
            out["weapon_b"] = d
        return out


class TeamInventory(db.Model):
    __tablename__ = "atr26_team_inventory"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    weapon_slug = db.Column(
        db.String(80), db.ForeignKey("atr26_weapons.slug", ondelete="CASCADE"), nullable=False
    )
    rolled_damage = db.Column(db.Integer, nullable=False)
    source_challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id"), nullable=True
    )
    card_draw_id = db.Column(
        db.Integer, db.ForeignKey("atr26_card_draws.id", ondelete="SET NULL"), nullable=True
    )
    acquired_date = db.Column(db.DateTime, default=datetime.utcnow)

    team = relationship("Teams", foreign_keys=[team_id])
    user = relationship("Users", foreign_keys=[user_id])
    card_draw = relationship("CardDraw", foreign_keys=[card_draw_id])

    @property
    def weapon(self):
        return Weapon.query.filter_by(slug=self.weapon_slug).first()

    def serialize(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "weapon": self.weapon.serialize() if self.weapon else None,
            "weapon_slug": self.weapon_slug,
            "rolled_damage": self.rolled_damage,
            "source_challenge_id": self.source_challenge_id,
            "card_draw_id": self.card_draw_id,
            "acquired_date": str(self.acquired_date),
        }


class TeamLoadout(db.Model):
    __tablename__ = "atr26_team_loadout"
    __table_args__ = (
        db.CheckConstraint(
            "(team_id IS NOT NULL AND user_id IS NULL) OR (team_id IS NULL AND user_id IS NOT NULL)",
            name="atr26_loadout_one_owner",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    slot_number = db.Column(db.Integer, nullable=False)
    inventory_id = db.Column(
        db.Integer, db.ForeignKey("atr26_team_inventory.id", ondelete="CASCADE"), nullable=False
    )
    submitted_at = db.Column(db.DateTime, nullable=True)

    team = relationship("Teams", foreign_keys=[team_id])
    inventory_item = relationship("TeamInventory", foreign_keys=[inventory_id])

    def serialize(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "slot_number": self.slot_number,
            "inventory_item": self.inventory_item.serialize() if self.inventory_item else None,
            "submitted_at": str(self.submitted_at) if self.submitted_at else None,
        }


class TeamHint(db.Model):
    __tablename__ = "atr26_team_hints"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    source_challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id"), nullable=True
    )
    hint_content = db.Column(db.Text, nullable=False)
    acquired_date = db.Column(db.DateTime, default=datetime.utcnow)

    team = relationship("Teams", foreign_keys=[team_id])

    def serialize(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "source_challenge_id": self.source_challenge_id,
            "hint_content": self.hint_content,
            "acquired_date": str(self.acquired_date),
        }


class BattleResult(db.Model):
    __tablename__ = "atr26_battle_results"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    bonus_points = db.Column(db.Integer, default=0)
    result_data = db.Column(db.Text, default="{}")
    battle_date = db.Column(db.DateTime, default=datetime.utcnow)

    team = relationship("Teams", foreign_keys=[team_id])

    def serialize(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "bonus_points": self.bonus_points,
            "result_data": self.result_data,
            "battle_date": str(self.battle_date),
        }
