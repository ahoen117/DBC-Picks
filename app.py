from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import requests
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from dbc_picks.db import (
    default_db_path,
    ensure_schema,
    get_connection,
    get_current_week,
    get_picks_for_current_draft,
    get_scoreboard_payload,
    list_drivers,
    list_players,
    save_draft_picks,
    seed_defaults_if_empty,
    set_current_week,
    lock_week_and_apply_scoring,
)
from dbc_picks.scoring import (
    compute_week_results,
    extract_event_short_name,
    extract_positions_by_last_name,
)


BASE_DIR = Path(__file__).resolve().parent

DB_PATH = default_db_path()

ADMIN_PASSWORD = os.getenv("DBC_PICKS_ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("DBC_PICKS_SECRET_KEY", "dev-secret-change-me")

if not ADMIN_PASSWORD:
    # Don't silently run a publicly writable admin surface.
    raise RuntimeError(
        "Missing DBC_PICKS_ADMIN_PASSWORD. Set it in your environment before running the server."
    )

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR))
app.secret_key = SECRET_KEY


def _with_db() -> Any:
    conn = get_connection(DB_PATH)
    try:
        ensure_schema(conn)
        seed_defaults_if_empty(conn)
        return conn
    except Exception:
        conn.close()
        raise


@app.get("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.get("/api/scoreboard")
def api_scoreboard():
    conn = _with_db()
    try:
        payload = get_scoreboard_payload(conn)
        return jsonify(payload)
    finally:
        conn.close()


@app.get("/api/current-picks")
def api_current_picks():
    conn = _with_db()
    try:
        picks = get_picks_for_current_draft(conn)
        players = list_players(conn)
        # Always return all players so the UI has a stable list.
        out: Dict[str, Dict[str, Any]] = {}
        for player in players:
            out[player] = {"pick": picks.get(player, "")}
        return jsonify(out)
    finally:
        conn.close()


def _require_admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))


@app.get("/admin/login")
def admin_login():
    error = request.args.get("error")
    return render_template("admin_login.html", error=error)


@app.post("/admin/login")
def admin_login_post():
    password = request.form.get("password", "")
    if password != ADMIN_PASSWORD:
        return redirect(url_for("admin_login", error="Incorrect password"))

    session["admin"] = True
    return redirect(url_for("admin_page"))


@app.get("/admin")
def admin_page():
    error = request.args.get("error")
    message = request.args.get("message")
    redirect_resp = _require_admin()
    if redirect_resp:
        return redirect_resp

    conn = _with_db()
    try:
        current_week = get_current_week(conn)
        players = list_players(conn)
        drivers = list_drivers(conn)
        current_picks = get_picks_for_current_draft(conn)
        return render_template(
            "admin.html",
            current_week=current_week,
            players=players,
            drivers=drivers,
            current_picks=current_picks,
            error=error,
            message=message,
        )
    finally:
        conn.close()


@app.post("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


@app.post("/admin/picks")
def admin_save_picks():
    redirect_resp = _require_admin()
    if redirect_resp:
        return redirect_resp

    conn = _with_db()
    try:
        current_week = get_current_week(conn)
        players = list_players(conn)
        picks_by_player = {p: request.form.get(p, "") for p in players}
        save_draft_picks(conn, week=current_week, picks_by_player=picks_by_player)
    except ValueError as e:
        return redirect(url_for("admin_page", error=str(e)))
    finally:
        conn.close()

    return redirect(url_for("admin_page"))

@app.post("/admin/finalize")
def admin_finalize_week():
    redirect_resp = _require_admin()
    if redirect_resp:
        return redirect_resp

    conn = _with_db()
    try:
        week = get_current_week(conn)
        players = list_players(conn)
        picks_by_player = get_picks_for_current_draft(conn)

        missing = [p for p in players if not picks_by_player.get(p)]
        if missing:
            raise ValueError(
                "Missing draft picks for: " + ", ".join(missing)
            )

        # Fetch latest race results from ESPN.
        url = os.getenv(
            "DBC_PICKS_ESPN_SCOREBOARD_URL",
            "https://site.api.espn.com/apis/site/v2/sports/racing/nascar-premier/scoreboard",
        )
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"ESPN request failed: {response.status_code}")

        json_data = response.json()
        race_name = extract_event_short_name(json_data)
        positions_by_last_name = extract_positions_by_last_name(json_data)

        lock_week_and_apply_scoring(
            conn,
            week=week,
            race_name=race_name,
            picks_by_player=picks_by_player,
            positions_by_last_name=positions_by_last_name,
            compute_results=compute_week_results,
        )

        # Advance the draft week.
        set_current_week(conn, week + 1)
    except Exception as e:
        return redirect(url_for("admin_page", error=str(e)))
    finally:
        conn.close()

    return redirect(url_for("admin_page", message=f"Finalized week {week}: {race_name}"))


if __name__ == "__main__":
    # Local dev runner. For production, use gunicorn/uvicorn.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)

