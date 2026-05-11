from flask import Blueprint, render_template

from CTFd.utils.decorators import authed_only

pages_bp = Blueprint(
    "atr26_game_pages",
    __name__,
    template_folder="../templates",
    url_prefix="/atr26_game",
)


@pages_bp.route("/inventory")
@authed_only
def inventory():
    return render_template("inventory.html")


@pages_bp.route("/loadout")
@authed_only
def loadout():
    return render_template("loadout.html")
