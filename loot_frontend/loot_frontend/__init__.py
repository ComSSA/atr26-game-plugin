from CTFd.plugins import (
    register_plugin_assets_directory,
    register_plugin_script,
    register_plugin_stylesheet,
)
from .api import loot_bp


def load(app):
    app.register_blueprint(loot_bp)
    register_plugin_assets_directory(app, base_path="/plugins/loot_frontend/assets/")
    register_plugin_stylesheet("/plugins/loot_frontend/assets/loot.css")
    register_plugin_script("/plugins/loot_frontend/assets/loot.js")
