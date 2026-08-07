"""Public and dashboard routes."""

from flask import render_template

from app.main import bp


@bp.route("/")
def index():
    """Landing page. Prompts the user to sign in or register."""
    return render_template("main/index.html")


@bp.route("/health")
def health():
    """Lightweight health-check endpoint used by Docker and CI."""
    from flask import jsonify

    return jsonify({"status": "ok", "service": "ai-code-assistant"})
