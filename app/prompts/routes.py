"""Prompt routes: CRUD, favorites, categories, and search."""

from flask import jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models import Prompt
from app.prompts import bp


def _get_prompt(prompt_id: int) -> Prompt:
    """Return the current user's prompt or abort with 404."""
    return Prompt.query.filter_by(id=prompt_id, user_id=current_user.id).first_or_404()


@bp.route("/")
@login_required
def index():
    """Render the prompt management page."""
    return render_template("prompts/index.html")


@bp.route("/api/prompts", methods=["GET"])
@login_required
def list_prompts():
    """Return prompts, optionally filtered by search query, category, or favorite."""
    query = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip()
    favorites_only = request.args.get("favorites") == "1"

    base = Prompt.query.filter_by(user_id=current_user.id)
    if query:
        base = base.filter(
            func.lower(Prompt.title).contains(query)
            | func.lower(Prompt.category).contains(query)
            | func.lower(Prompt.content).contains(query)
        )
    if category:
        base = base.filter(Prompt.category == category)
    if favorites_only:
        base = base.filter(Prompt.is_favorite.is_(True))

    prompts = base.order_by(Prompt.is_favorite.desc(), Prompt.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in prompts])


@bp.route("/api/categories", methods=["GET"])
@login_required
def list_categories():
    """Return the distinct prompt categories used by the current user."""
    rows = (
        db.session.query(func.distinct(Prompt.category))
        .filter(Prompt.user_id == current_user.id)
        .all()
    )
    return jsonify([row[0] for row in rows])


@bp.route("/api/prompts", methods=["POST"])
@login_required
def create_prompt():
    """Create a new prompt template."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "Both title and content are required."}), 400

    prompt = Prompt(
        user_id=current_user.id,
        title=title[:200],
        content=content,
        category=(data.get("category") or "General").strip()[:80] or "General",
        is_favorite=bool(data.get("is_favorite")),
    )
    db.session.add(prompt)
    db.session.commit()
    return jsonify(prompt.to_dict()), 201


@bp.route("/api/prompts/<int:prompt_id>", methods=["GET"])
@login_required
def get_prompt(prompt_id: int):
    """Return a single prompt."""
    prompt = _get_prompt(prompt_id)
    return jsonify(prompt.to_dict())


@bp.route("/api/prompts/<int:prompt_id>", methods=["PATCH"])
@login_required
def update_prompt(prompt_id: int):
    """Update a prompt's fields (title, content, category, favorite)."""
    prompt = _get_prompt(prompt_id)
    data = request.get_json(silent=True) or {}
    if "title" in data:
        prompt.title = (data.get("title") or prompt.title).strip()[:200]
    if "content" in data:
        prompt.content = (data.get("content") or "").strip()
        if not prompt.content:
            return jsonify({"error": "Content cannot be empty."}), 400
    if "category" in data:
        prompt.category = (data.get("category") or "General").strip()[:80] or "General"
    if "is_favorite" in data:
        prompt.is_favorite = bool(data["is_favorite"])
    db.session.commit()
    return jsonify(prompt.to_dict())


@bp.route("/api/prompts/<int:prompt_id>", methods=["DELETE"])
@login_required
def delete_prompt(prompt_id: int):
    """Delete a prompt template."""
    prompt = _get_prompt(prompt_id)
    db.session.delete(prompt)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/api/prompts/<int:prompt_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(prompt_id: int):
    """Toggle the favorite flag on a prompt."""
    prompt = _get_prompt(prompt_id)
    prompt.is_favorite = not prompt.is_favorite
    db.session.commit()
    return jsonify(prompt.to_dict())
