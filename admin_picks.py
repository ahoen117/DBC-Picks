#!/usr/bin/env python3
"""DBC Picks admin.

Drop this file next to dbcPicks.db and PlayerStats.json, then run:

    python admin_picks.py

Open http://127.0.0.1:8765

Each player's dropdown hides drivers already stored in the picks table.
Save writes PlayerStats.json (and a .bak). It does not score the race
and it does not change the database. Run DBC-Picks.py after the race
the same way you do now.
"""

from __future__ import annotations

import json
import sqlite3
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "dbcPicks.db"
PICKS_PATH = ROOT / "PlayerStats.json"
SITE_PATH = ROOT / "Website" / "picks-data.json"
FALLBACK_SITE = ROOT / "picks-data.json"
HOST = "127.0.0.1"
PORT = 8765


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_pick_order(players):
    for path in (SITE_PATH, FALLBACK_SITE):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        order = [name for name in data.get("sorted_results", []) if name in players]
        rest = [name for name in players if name not in order]
        return order + rest, data.get("race_name", "")
    return sorted(players), ""


def load_state():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No database at {DB_PATH}")

    conn = connect()
    cur = conn.cursor()
    players = [row["player_name"] for row in cur.execute(
        "SELECT player_name FROM players ORDER BY player_name"
    )]
    drivers = [row["driver_name"] for row in cur.execute(
        "SELECT driver_name FROM drivers ORDER BY driver_name"
    )]
    used = {name: [] for name in players}
    for row in cur.execute(
        "SELECT player_name, driver, week FROM picks ORDER BY week, id"
    ):
        used.setdefault(row["player_name"], []).append(
            {"driver": row["driver"], "week": row["week"]}
        )
    week_row = cur.execute(
        "SELECT value FROM config WHERE key = 'current_week'"
    ).fetchone()
    conn.close()

    current = {}
    if PICKS_PATH.exists():
        raw = json.loads(PICKS_PATH.read_text(encoding="utf-8"))
        for name, info in raw.items():
            if isinstance(info, dict):
                current[name] = (info.get("pick") or "").strip()
            elif isinstance(info, str):
                current[name] = info.strip()

    order, last_race = load_pick_order(players)
    return {
        "players": order,
        "drivers": drivers,
        "used": used,
        "current": current,
        "week": week_row["value"] if week_row else None,
        "last_race": last_race,
        "picks_path": str(PICKS_PATH),
    }


def save_picks(payload):
    state = load_state()
    driver_set = set(state["drivers"])
    used = {
        name: {item["driver"] for item in items}
        for name, items in state["used"].items()
    }
    incoming = payload.get("picks", {})
    cleaned = {}
    errors = []

    for name in state["players"]:
        pick = str(incoming.get(name, "") or "").strip()
        if not pick:
            cleaned[name] = {"pick": ""}
            continue
        if pick not in driver_set:
            errors.append(f"{name}: {pick} is not on the driver list")
            continue
        if pick in used.get(name, set()):
            errors.append(f"{name} already used {pick}")
            continue
        cleaned[name] = {"pick": pick}

    if errors:
        return {"ok": False, "errors": errors}

    if PICKS_PATH.exists():
        backup = PICKS_PATH.with_suffix(".json.bak")
        backup.write_text(PICKS_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    PICKS_PATH.write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    filled = sum(1 for info in cleaned.values() if info["pick"])
    return {
        "ok": True,
        "saved": cleaned,
        "filled": filled,
        "total": len(cleaned),
        "path": str(PICKS_PATH),
        "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DBC Picks admin</title>
  <style>
    :root {
      --bg: #1c1c1c;
      --panel: #2a2a2a;
      --panel-2: #333;
      --line: #4a4a4a;
      --text: #f4f4f4;
      --muted: #b9b9b9;
      --red: #d61717;
      --green: #3f9d45;
      --gold: #e2c14a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      padding: 28px 24px 18px;
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0 0 6px; font-size: 28px; }
    .sub { color: var(--muted); margin: 0; }
    main { padding: 22px 24px 110px; max-width: 1180px; margin: 0 auto; }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 16px 0 22px;
    }
    .pill {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 12px;
      color: var(--muted);
      font-size: 13px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
    }
    .card.head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 10px;
    }
    .order {
      color: var(--gold);
      font-size: 13px;
      font-weight: bold;
    }
    h2 { margin: 0; font-size: 20px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; }
    .combo { position: relative; }
    .combo input {
      width: 100%;
      background: #222;
      color: white;
      border: 1px solid #666;
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 15px;
    }
    .combo input:focus { outline: 2px solid var(--green); border-color: var(--green); }
    .menu {
      display: none;
      position: absolute;
      z-index: 5;
      left: 0;
      right: 0;
      max-height: 240px;
      overflow: auto;
      background: #161616;
      border: 1px solid #666;
      border-radius: 8px;
      margin-top: 4px;
    }
    .menu.open { display: block; }
    .opt {
      padding: 9px 12px;
      cursor: pointer;
    }
    .opt:hover, .opt.active { background: #3a3a3a; }
    .empty { padding: 10px 12px; color: var(--muted); }
    .used { margin-top: 12px; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .chip {
      background: #4a1d1d;
      color: #ffd0d0;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
    }
    .note { color: var(--muted); font-size: 13px; margin-top: 8px; }
    .bar {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 24px;
      background: #141414;
      border-top: 1px solid var(--line);
    }
    button {
      background: var(--green);
      color: white;
      border: 0;
      border-radius: 8px;
      padding: 12px 18px;
      font-size: 15px;
      font-weight: bold;
      cursor: pointer;
    }
    button:disabled { opacity: 0.6; cursor: default; }
    #status { color: var(--muted); }
    #status.ok { color: #9be7a0; }
    #status.bad { color: #ff9d9d; }
    .dup { color: var(--gold); }
  </style>
</head>
<body>
  <header>
    <h1>DBC Picks admin</h1>
    <p class="sub">Dropdowns hide drivers that player has already used. Saving writes PlayerStats.json only.</p>
  </header>
  <main>
    <div class="meta" id="meta"></div>
    <div class="grid" id="grid"></div>
  </main>
  <div class="bar">
    <div id="status">Loading…</div>
    <button id="save" disabled>Save picks</button>
  </div>
  <script>
    let state = null;
    const chosen = {};

    function availableFor(player) {
      const used = new Set((state.used[player] || []).map(item => item.driver));
      return state.drivers.filter(driver => !used.has(driver));
    }

    function duplicateMap() {
      const counts = {};
      Object.values(chosen).forEach(driver => {
        if (!driver) return;
        counts[driver] = (counts[driver] || 0) + 1;
      });
      return counts;
    }

    function render() {
      const meta = document.getElementById('meta');
      meta.innerHTML = [
        `Next entry week ${state.week ?? "—"}`,
        state.last_race ? `Last scored: ${state.last_race}` : "No last race label",
        `${state.players.length} players`,
        `${state.drivers.length} drivers on the list`
      ].map(text => `<span class="pill">${text}</span>`).join("");

      const grid = document.getElementById('grid');
      grid.innerHTML = "";
      state.players.forEach((player, index) => {
        const used = state.used[player] || [];
        const current = chosen[player] || "";
        const card = document.createElement('section');
        card.className = 'card';
        card.innerHTML = `
          <div class="head">
            <h2>${player}</h2>
            <span class="order">Pick ${index + 1}</span>
          </div>
          <label for="pick-${player}">This week</label>
          <div class="combo" data-player="${player}">
            <input id="pick-${player}" placeholder="Choose a driver" autocomplete="off" value="${current}">
            <div class="menu"></div>
          </div>
          <div class="note" data-note></div>
          <div class="used">
            <label>Already used, hidden from the list</label>
            <div class="chips">
              ${used.length ? used.map(item => `<span class="chip">${item.driver} · wk ${item.week}</span>`).join("") : "<span class='note'>None yet</span>"}
            </div>
          </div>
        `;
        grid.appendChild(card);
      });
      bindCombos();
      refreshNotes();
      document.getElementById('save').disabled = false;
      document.getElementById('status').textContent = "Unsaved changes stay in the browser until you save.";
    }

    function bindCombos() {
      document.querySelectorAll('.combo').forEach(combo => {
        const player = combo.dataset.player;
        const input = combo.querySelector('input');
        const menu = combo.querySelector('.menu');

        function openMenu() {
          const query = input.value.trim().toLowerCase();
          const options = availableFor(player).filter(driver => driver.toLowerCase().includes(query));
          menu.innerHTML = options.length
            ? options.map(driver => `<div class="opt" data-driver="${driver}">${driver}</div>`).join("")
            : `<div class="empty">No matching unused driver</div>`;
          menu.classList.add('open');
        }

        input.addEventListener('focus', openMenu);
        input.addEventListener('input', () => {
          chosen[player] = "";
          openMenu();
          refreshNotes();
        });
        menu.addEventListener('mousedown', event => {
          const opt = event.target.closest('.opt');
          if (!opt) return;
          chosen[player] = opt.dataset.driver;
          input.value = opt.dataset.driver;
          menu.classList.remove('open');
          refreshNotes();
        });
        input.addEventListener('blur', () => {
          setTimeout(() => menu.classList.remove('open'), 120);
          const match = availableFor(player).find(driver => driver.toLowerCase() === input.value.trim().toLowerCase());
          if (match) {
            chosen[player] = match;
            input.value = match;
          } else if (!chosen[player]) {
            input.value = "";
          }
          refreshNotes();
        });
      });
    }

    function refreshNotes() {
      const dups = duplicateMap();
      document.querySelectorAll('.combo').forEach(combo => {
        const player = combo.dataset.player;
        const note = combo.parentElement.querySelector('[data-note]');
        const pick = chosen[player];
        if (!pick) {
          note.textContent = `${availableFor(player).length} drivers still available`;
          note.className = 'note';
          return;
        }
        if (dups[pick] > 1) {
          note.textContent = `${pick} is also picked by another player this week. That is allowed.`;
          note.className = 'note dup';
          return;
        }
        note.textContent = `${pick} selected`;
        note.className = 'note';
      });
      const filled = Object.values(chosen).filter(Boolean).length;
      const status = document.getElementById('status');
      if (!status.dataset.locked) {
        status.textContent = `${filled} of ${state.players.length} picks entered`;
        status.className = '';
      }
    }

    async function init() {
      const res = await fetch('/api/state');
      state = await res.json();
      state.players.forEach(player => {
        const pick = state.current[player] || "";
        const used = new Set((state.used[player] || []).map(item => item.driver));
        chosen[player] = pick && !used.has(pick) ? pick : "";
      });
      render();
    }

    document.getElementById('save').addEventListener('click', async () => {
      const button = document.getElementById('save');
      const status = document.getElementById('status');
      button.disabled = true;
      status.dataset.locked = "1";
      status.className = '';
      status.textContent = "Saving…";
      const res = await fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ picks: chosen })
      });
      const data = await res.json();
      button.disabled = false;
      delete status.dataset.locked;
      if (!data.ok) {
        status.className = 'bad';
        status.textContent = data.errors.join(' · ');
        return;
      }
      status.className = 'ok';
      status.textContent = `Saved ${data.filled} of ${data.total} picks to PlayerStats.json at ${data.when}`;
    });

    init();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        if path == "/api/state":
            try:
                self._send(200, json.dumps(load_state()), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "errors": [str(exc)]}), "application/json")
            return
        self._send(404, "Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/save":
            self._send(404, "Not found", "text/plain; charset=utf-8")
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            result = save_picks(payload)
        except Exception as exc:
            result = {"ok": False, "errors": [str(exc)]}
        self._send(200 if result.get("ok") else 400, json.dumps(result), "application/json")

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Put admin_picks.py next to dbcPicks.db. Missing {DB_PATH}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"DBC Picks admin at {url}")
    print(f"Reading {DB_PATH}")
    print(f"Saving {PICKS_PATH}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server.serve_forever()


if __name__ == "__main__":
    main()
