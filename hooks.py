"""SQLAlchemy hooks: create CardDraw in the same commit as a new Solve when loot tags apply."""

from sqlalchemy import event
from sqlalchemy.orm import Session


def register_solve_loot_hooks(app):
    @event.listens_for(Session, "before_flush")
    def _atr26_collect_new_solves(session, flush_context, instances=None):
        from CTFd.models import Solves

        key = "_atr26_loot_solves_pending"
        batch = []
        for obj in list(session.new):
            if isinstance(obj, Solves):
                batch.append(obj)
        if batch:
            session.info[key] = session.info.get(key, []) + batch

    @event.listens_for(Session, "after_flush")
    def _atr26_emit_card_draws(session, flush_context):
        from CTFd.models import Solves

        from .loot import roll_card_draw_for_solve
        from .models import CardDraw

        key = "_atr26_loot_solves_pending"
        pending = session.info.pop(key, None)
        if not pending:
            return

        for solve in pending:
            if not isinstance(solve, Solves):
                continue
            if solve.id is None:
                continue
            if session.query(CardDraw).filter_by(solve_id=solve.id).first():
                continue
            draw = roll_card_draw_for_solve(solve)
            if draw is None:
                continue
            session.add(draw)
