"""Flask REST API + LINE webhook for the apartment billing web app.

Run from the project root:
    python -m src.api          (listens on 127.0.0.1:5000)

When frontend/dist exists (after `npm run build`), the same server also serves
the React SPA at "/". In development, use the Vite dev server on :5173 with its
`/api` proxy instead.
"""

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

import src.auth as auth
import src.database as db
import src.service as service
from src.database import DataNotFoundError

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "frontend" / "dist"


def create_app():
    app = Flask(__name__, static_folder=None)
    CORS(app, resources={
        r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]},
    })

    @app.errorhandler(DataNotFoundError)
    def _data_not_found(error):
        return jsonify({"error": str(error)}), 409

    @app.errorhandler(ValueError)
    def _bad_request(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(RuntimeError)
    def _server_error(error):
        return jsonify({"error": str(error)}), 500

    # ---- auth ----

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        body = request.get_json(silent=True) or {}
        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        if auth.verify_admin(username, password):
            return jsonify({"token": auth.create_token(username), "username": username})
        return jsonify({"error": "Invalid username or password"}), 401

    @app.route("/api/auth/me", methods=["GET"])
    @auth.require_auth
    def me():
        return jsonify({"username": auth.get_current_username()})

    # ---- workflow ----

    @app.route("/api/state", methods=["GET"])
    @auth.require_auth
    def state():
        return jsonify(service.get_state())

    @app.route("/api/cycle/new", methods=["POST"])
    @auth.require_auth
    def cycle_new():
        body = request.get_json(silent=True) or {}
        result = service.start_new_cycle(
            billing_month=body.get("billing_month"),
            bill_date=body.get("bill_date"),
        )
        return jsonify(result)

    @app.route("/api/meters", methods=["GET"])
    @auth.require_auth
    def meters():
        return jsonify(service.get_meters())

    @app.route("/api/meters/current", methods=["PUT"])
    @auth.require_auth
    def meters_current():
        body = request.get_json(silent=True) or {}
        return jsonify(service.save_current_meters(body.get("rooms", {})))

    @app.route("/api/drc/detect", methods=["POST"])
    @auth.require_auth
    def drc_detect():
        return jsonify({"issues": service.detect_drc_issues()})

    @app.route("/api/drc/apply", methods=["POST"])
    @auth.require_auth
    def drc_apply():
        body = request.get_json(silent=True) or {}
        return jsonify(service.apply_drc_fixes(body.get("fixes", [])))

    @app.route("/api/bills/generate", methods=["POST"])
    @auth.require_auth
    def bills_generate():
        return jsonify(service.generate_bills_and_pdf())

    @app.route("/api/bills/pdf", methods=["GET"])
    @auth.require_auth
    def bills_pdf():
        if not service.PDF_PATH.exists():
            return jsonify({"error": "PDF not found — generate the bill first."}), 404
        return send_file(str(service.PDF_PATH), mimetype="application/pdf")

    @app.route("/api/bills/convert", methods=["POST"])
    @auth.require_auth
    def bills_convert():
        return jsonify(service.convert_pdf_to_jpegs())

    @app.route("/api/upload", methods=["POST"])
    @auth.require_auth
    def upload():
        return jsonify(service.upload_bills())

    @app.route("/api/uploaded_urls", methods=["GET"])
    @auth.require_auth
    def uploaded_urls():
        return jsonify(service.get_uploaded_urls())

    @app.route("/api/send", methods=["POST"])
    @auth.require_auth
    def send():
        return jsonify(service.send_bills())

    # ---- LINE webhook (captures tenant room -> LINE user id) ----

    @app.route("/webhook", methods=["POST"])
    def webhook():
        body = request.get_json(silent=True) or {}
        if "events" in body:
            for event in body["events"]:
                if event.get("type") == "message" and event.get("message", {}).get("type") == "text":
                    user_id = event["source"]["userId"]
                    room = event["message"]["text"]
                    db.set_tenant_line_id(room, user_id)
        return "OK", 200

    # ---- serve the built React app (frontend/dist) ----

    if DIST_DIR.exists():
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def spa(path):
            if path.startswith("api/") or path == "webhook":
                return jsonify({"error": "Not found"}), 404
            target = DIST_DIR / path
            if path and target.is_file():
                return send_from_directory(str(DIST_DIR), path)
            return send_from_directory(str(DIST_DIR), "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"🚀 API server on http://127.0.0.1:{port} (webhook: POST /webhook)")
    app.run(host="127.0.0.1", port=port, debug=False)
