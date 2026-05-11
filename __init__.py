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
