from CTFd.plugins import (
    register_admin_plugin_menu_bar,
    register_plugin_assets_directory,
    register_plugin_script,
    register_plugin_stylesheet,
    register_user_page_menu_bar,
)

from .models import *  # noqa: F401,F403 — registers all models with SQLAlchemy


def load(app):
    app.db.create_all()

    from .hooks import register_solve_loot_hooks

    register_solve_loot_hooks(app)

    @app.cli.command("atr26-seed-weapons")
    def atr26_seed_weapons_cli():
        """Load or update Weapon rows from weapons_seed.json in the plugin directory."""
        import json
        import os

        from .seed import upsert_weapons_from_records

        root = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(root, "weapons_seed.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "weapons" in data:
            records = data["weapons"]
        else:
            records = data
        c, u = upsert_weapons_from_records(records)
        print(f"atr26-seed-weapons: created={c} updated={u} ({path})")

    @app.cli.command("atr26-seed-test-challenges")
    def atr26_seed_test_challenges_cli():
        """Insert ATR26-branded standard challenges with flags and loot tags (idempotent)."""
        from .seed_challenges import seed_test_challenges

        created, skipped = seed_test_challenges()
        print(f"atr26-seed-test-challenges: created={created} skipped={skipped}")

    register_plugin_assets_directory(app, base_path="/plugins/atr26_game/assets/")

    register_plugin_script("/plugins/atr26_game/assets/js/card-select.js")
    register_plugin_stylesheet("/plugins/atr26_game/assets/css/atr26-game.css")

    register_user_page_menu_bar("Inventory", "/atr26_game/inventory")
    register_user_page_menu_bar("Loadout", "/atr26_game/loadout")

    register_admin_plugin_menu_bar("ATR26 Game", "/atr26_game/admin/weapons")

    from .blueprints.admin import admin_bp
    from .blueprints.api import api_bp
    from .blueprints.pages import pages_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pages_bp)
