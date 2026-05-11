from datetime import datetime

from sqlalchemy.orm import relationship

from CTFd.models import db


class Weapon(db.Model):
    __tablename__ = "atr26_weapons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default="")
    rarity = db.Column(db.String(32), nullable=False, default="common")
    damage_type = db.Column(db.String(64), nullable=False, default="physical")
    icon_path = db.Column(db.Text, default="")
    card_border_color = db.Column(db.String(7), default="#808080")
    base_damage = db.Column(db.Integer, default=0)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rarity": self.rarity,
            "damage_type": self.damage_type,
            "icon_path": self.icon_path,
            "card_border_color": self.card_border_color,
            "base_damage": self.base_damage,
        }


class LootTable(db.Model):
    __tablename__ = "atr26_loot_table"
    __table_args__ = (
        db.UniqueConstraint("challenge_id", "weapon_id", name="uq_loot_challenge_weapon"),
    )

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    weapon_id = db.Column(
        db.Integer, db.ForeignKey("atr26_weapons.id", ondelete="CASCADE"), nullable=False
    )
    weight = db.Column(db.Integer, default=1, nullable=False)

    challenge = relationship("Challenges", foreign_keys=[challenge_id])
    weapon = relationship("Weapon", foreign_keys=[weapon_id])

    def serialize(self):
        return {
            "id": self.id,
            "challenge_id": self.challenge_id,
            "weapon_id": self.weapon_id,
            "weight": self.weight,
        }


class PendingCardOffer(db.Model):
    __tablename__ = "atr26_pending_offers"
    __table_args__ = (
        db.UniqueConstraint("team_id", "challenge_id", name="uq_offer_team_challenge"),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    weapon_id_a = db.Column(
        db.Integer, db.ForeignKey("atr26_weapons.id"), nullable=False
    )
    weapon_id_b = db.Column(
        db.Integer, db.ForeignKey("atr26_weapons.id"), nullable=False
    )
    selected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = relationship("Teams", foreign_keys=[team_id])
    weapon_a = relationship("Weapon", foreign_keys=[weapon_id_a])
    weapon_b = relationship("Weapon", foreign_keys=[weapon_id_b])

    def serialize(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "challenge_id": self.challenge_id,
            "weapon_a": self.weapon_a.serialize() if self.weapon_a else None,
            "weapon_b": self.weapon_b.serialize() if self.weapon_b else None,
            "selected": self.selected,
            "created_at": str(self.created_at),
        }


class TeamInventory(db.Model):
    __tablename__ = "atr26_team_inventory"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    weapon_id = db.Column(
        db.Integer, db.ForeignKey("atr26_weapons.id", ondelete="CASCADE"), nullable=False
    )
    source_challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id"), nullable=True
    )
    acquired_date = db.Column(db.DateTime, default=datetime.utcnow)

    team = relationship("Teams", foreign_keys=[team_id])
    weapon = relationship("Weapon", foreign_keys=[weapon_id])

    def serialize(self):
        return {
            "id": self.id,
            "team_id": self.team_id,
            "weapon": self.weapon.serialize() if self.weapon else None,
            "source_challenge_id": self.source_challenge_id,
            "acquired_date": str(self.acquired_date),
        }


class TeamLoadout(db.Model):
    __tablename__ = "atr26_team_loadout"
    __table_args__ = (
        db.UniqueConstraint("team_id", "slot_number", name="uq_loadout_team_slot"),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
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
