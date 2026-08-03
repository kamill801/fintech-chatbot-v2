from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Response, jsonify, send_from_directory


def create_web_blueprint(build_dir: Path) -> Blueprint:
    web = Blueprint("ledger_web", __name__)

    def index() -> Response:
        if not (build_dir / "index.html").is_file():
            return jsonify({"error": {"code": "frontend_not_built", "message": "frontend build is unavailable"}}), 404
        return send_from_directory(build_dir, "index.html")

    @web.get("/")
    def root() -> Response:
        return index()

    @web.get("/<path:path>")
    def spa(path: str) -> Response:
        candidate = build_dir / path
        if candidate.is_file():
            return send_from_directory(build_dir, path)
        if path.startswith(("api/", "health", "ready", "question")):
            return jsonify({"error": {"code": "not_found", "message": "route was not found"}}), 404
        return index()

    return web
