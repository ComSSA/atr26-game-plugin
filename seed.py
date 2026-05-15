"""Upsert Weapon catalog rows from structured dicts (JSON / API)."""

from CTFd.models import db

from .models import Weapon


def upsert_weapons_from_records(records: list) -> tuple[int, int]:
    """
    Merge weapons by slug. Returns (created_count, updated_count).
    Each record: slug, name, rarity, damage_type, icon (or icon_path), enabled (optional), description, card_border_color.
    """
    created = 0
    updated = 0
    for raw in records:
        if not isinstance(raw, dict):
            continue
        slug = str(raw.get("slug", "")).strip().lower()
        if not slug:
            continue
        existing = Weapon.query.filter_by(slug=slug).first()
        name = str(raw.get("name", slug)).strip() or slug
        rarity = str(raw.get("rarity", "common")).strip().lower() or "common"
        damage_type = str(raw.get("damage_type", "physical")).strip() or "physical"
        icon = raw.get("icon", raw.get("icon_path", ""))
        if icon is None:
            icon = ""
        icon = str(icon)
        enabled = bool(raw.get("enabled", True))
        description = str(raw.get("description", "") or "")
        border = str(raw.get("card_border_color", "#808080") or "#808080")

        if existing:
            existing.name = name
            existing.description = description
            existing.rarity = rarity
            existing.damage_type = damage_type
            existing.icon_path = icon
            existing.card_border_color = border
            existing.enabled = enabled
            updated += 1
        else:
            db.session.add(
                Weapon(
                    slug=slug,
                    name=name,
                    description=description,
                    rarity=rarity,
                    damage_type=damage_type,
                    icon_path=icon,
                    card_border_color=border,
                    enabled=enabled,
                )
            )
            created += 1

    db.session.commit()
    return created, updated
