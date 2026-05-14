"""Create repeatable ATR26 test challenges (flags + loot tags) for local QA."""

from sqlalchemy import func

from CTFd.cache import clear_challenges
from CTFd.models import Challenges, Flags, Tags, db

# Prefix used to detect / skip already-seeded rows on re-run.
NAME_PREFIX = "[ATR26 Test]"

# (name suffix after prefix, category, value, flag content, tag values)
_TEST_ROWS = [
    ("Easy loot", "ATR26", 10, "atr26{easy_loot}", ["loot:easy"]),
    ("Medium loot", "ATR26", 20, "atr26{medium_loot}", ["loot:medium"]),
    ("Hard loot", "ATR26", 30, "atr26{hard_loot}", ["loot:hard"]),
    ("Hard wins over medium", "ATR26", 25, "atr26{hard_wins}", ["loot:medium", "loot:hard"]),
    ("Loot disabled", "ATR26", 15, "atr26{loot_off}", ["loot:easy", "loot:off"]),
    ("No loot tag", "ATR26", 5, "atr26{no_loot_tag}", []),
    ("Easy loot B", "ATR26", 12, "atr26{easy_loot_b}", ["loot:easy"]),
    ("Warmup static", "Misc", 1, "atr26{warmup}", []),
]


def seed_test_challenges() -> tuple[int, int]:
    """
    Insert standard challenges with static flags and optional loot tags.
    Skips any challenge whose name already equals the target name.
    Returns (created_count, skipped_count).
    """
    created = 0
    skipped = 0

    base_pos = db.session.query(func.max(Challenges.position)).scalar() or 0

    for i, (suffix, category, value, flag_content, tag_values) in enumerate(_TEST_ROWS):
        full_name = f"{NAME_PREFIX} {suffix}"
        existing = Challenges.query.filter_by(name=full_name).first()
        if existing:
            skipped += 1
            continue

        chal = Challenges(
            name=full_name[:80],
            description=f"Test challenge for ATR26 loot. Submit flag: `{flag_content}`",
            category=category[:80],
            value=value,
            type="standard",
            state="visible",
            logic="any",
            position=base_pos + i + 1,
        )
        db.session.add(chal)
        db.session.flush()

        db.session.add(
            Flags(
                challenge_id=chal.id,
                type="static",
                content=flag_content,
                data=None,
            )
        )
        for tv in tag_values:
            db.session.add(Tags(challenge_id=chal.id, value=tv[:80]))

        created += 1

    db.session.commit()
    clear_challenges()
    return created, skipped
