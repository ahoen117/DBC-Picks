from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

from dbc_picks.scoring import WeeklyScore


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "dbcPicks.db"


def default_db_path() -> Path:
    env = os.getenv("DBC_PICKS_DB_PATH")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_txn(conn: sqlite3.Connection) -> Iterator[sqlite3.Cursor]:
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    for row in cur.fetchall():
        if row[1] == column_name:  # row: (cid, name, type, notnull, dflt_value, pk)
            return True
    return False


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Creates the minimal tables/columns we need for:
    - drafting weekly picks
    - finalizing a week by fetching ESPN results and scoring
    - serving the dynamic JSON used by the web UI
    """
    with db_txn(conn) as cur:
        # players: season totals
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                player_name TEXT PRIMARY KEY,
                total_points INTEGER DEFAULT 0
            )
            """
        )

        # drivers: roster for dropdowns and validation
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS drivers (
                driver_name TEXT PRIMARY KEY
            )
            """
        )

        # config: current week number
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        if not _column_exists(conn, "config", "value"):
            raise RuntimeError("Unexpected config schema: missing column 'value'.")

        # Set a default current_week if absent.
        cur.execute("SELECT value FROM config WHERE key='current_week'")
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO config(key, value) VALUES(?, ?)", ("current_week", "1"))

        # weeklyPoints: last finalized week points (used by UI)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weeklyPoints (
                player_name TEXT PRIMARY KEY,
                weekly_points INTEGER DEFAULT 0
            )
            """
        )

        # picks: season pick history plus "is_current_pick" for the draft week
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                driver TEXT NOT NULL,
                week INTEGER NOT NULL,
                is_current_pick INTEGER DEFAULT 0,
                picked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # weeks: tracks finalized weeks so we can compute pick order + show race name.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weeks (
                week_number INTEGER PRIMARY KEY,
                race_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finalized_at TIMESTAMP,
                last_updated TIMESTAMP,
                locked INTEGER DEFAULT 0
            )
            """
        )

        # week_results: per-player scoring for finalized weeks.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS week_results (
                week_number INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                picked_driver TEXT NOT NULL,
                finish_pos INTEGER NOT NULL,
                weekly_points INTEGER NOT NULL,
                bonus_points INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (week_number, player_name)
            )
            """
        )


def seed_defaults_if_empty(conn: sqlite3.Connection, *, players: Optional[List[str]] = None) -> None:
    if players is None:
        players = [
            "David",
            "Randy",
            "Travis",
            "Will",
            "Aaron",
            "Quentin",
            "Taylor",
            "Dakota",
            "Tomas",
        ]

    with db_txn(conn) as cur:
        cur.execute("SELECT COUNT(*) AS c FROM players")
        if cur.fetchone()["c"] == 0:
            for p in players:
                cur.execute(
                    "INSERT OR REPLACE INTO players(player_name, total_points) VALUES (?, ?)",
                    (p, 0),
                )

        cur.execute("SELECT COUNT(*) AS c FROM weeklyPoints")
        if cur.fetchone()["c"] == 0:
            for p in players:
                cur.execute(
                    "INSERT OR REPLACE INTO weeklyPoints(player_name, weekly_points) VALUES (?, ?)",
                    (p, 0),
                )


def get_current_week(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    cur.execute("SELECT value FROM config WHERE key='current_week'")
    row = cur.fetchone()
    return int(row["value"])


def set_current_week(conn: sqlite3.Connection, week: int) -> None:
    with db_txn(conn):
        conn.execute("UPDATE config SET value=? WHERE key='current_week'", (str(week),))


def get_latest_finalized_week_number(conn: sqlite3.Connection) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("SELECT week_number FROM weeks WHERE locked=1 ORDER BY week_number DESC LIMIT 1")
    row = cur.fetchone()
    return int(row["week_number"]) if row else None


def get_race_name_for_week(conn: sqlite3.Connection, week_number: int) -> Optional[str]:
    cur = conn.cursor()
    cur.execute("SELECT race_name FROM weeks WHERE week_number=?", (week_number,))
    row = cur.fetchone()
    return row["race_name"] if row else None


def list_players(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT player_name FROM players ORDER BY player_name")
    return [r["player_name"] for r in cur.fetchall()]


def list_drivers(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT driver_name FROM drivers ORDER BY driver_name")
    return [r["driver_name"] for r in cur.fetchall()]


def delete_picks_for_week(conn: sqlite3.Connection, week: int) -> None:
    with db_txn(conn):
        conn.execute("DELETE FROM picks WHERE week=?", (week,))


def get_picks_for_current_draft(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    Returns {player_name: driver} for picks marked is_current_pick=1.
    """
    cur = conn.cursor()
    cur.execute("SELECT player_name, driver FROM picks WHERE is_current_pick=1")
    out: Dict[str, str] = {}
    for row in cur.fetchall():
        out[row["player_name"]] = row["driver"]
    return out


def save_draft_picks(conn: sqlite3.Connection, *, week: int, picks_by_player: Mapping[str, str]) -> None:
    """
    Replaces the current draft picks for the given week.
    """
    players = list_players(conn)
    drivers = set(list_drivers(conn))

    missing_players = [p for p in players if p not in picks_by_player]
    if missing_players:
        raise ValueError(f"Missing picks for players: {', '.join(missing_players)}")

    invalid_drivers = [d for d in picks_by_player.values() if d not in drivers]
    if invalid_drivers:
        raise ValueError(f"Invalid driver(s): {', '.join(sorted(set(invalid_drivers)))}")

    # Allow re-drafting for the draft week; enforce season uniqueness in code.
    with db_txn(conn) as cur:
        cur.execute("DELETE FROM picks WHERE week=?", (week,))

        for player_name, driver in picks_by_player.items():
            # Enforce the legacy "player can pick a driver only once this season".
            cur.execute(
                """
                SELECT COUNT(*) AS c
                FROM picks
                WHERE player_name=? AND driver=?
                AND week<>?
                """,
                (player_name, driver, week),
            )
            if cur.fetchone()["c"] > 0:
                raise ValueError(f"{player_name} already picked {driver} this season")

            cur.execute(
                """
                INSERT INTO picks(player_name, driver, week, is_current_pick)
                VALUES (?, ?, ?, 1)
                """,
                (player_name, driver, week),
            )


def lock_week_and_apply_scoring(
    conn: sqlite3.Connection,
    *,
    week: int,
    race_name: str,
    picks_by_player: Mapping[str, str],
    positions_by_last_name: Mapping[str, int],
    compute_results,
) -> Dict[str, WeeklyScore]:
    """
    compute_results is injected so callers can decide which scoring rules to apply.
    Expected signature:
      compute_results(players_to_picks, positions_by_last_name) -> (sorted_results, score_by_player, next_pick_order)
    """
    sorted_results, score_by_player, _next_pick_order = compute_results(
        players_to_picks=picks_by_player,
        positions_by_last_name=positions_by_last_name,
    )

    # If any player is missing from the scoring results (shouldn't happen), fail fast.
    missing = [p for p in picks_by_player.keys() if p not in score_by_player]
    if missing:
        raise RuntimeError(f"Scoring did not produce results for: {', '.join(missing)}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    with db_txn(conn) as cur:
        # Mark week as finalized/locked.
        cur.execute(
            """
            INSERT INTO weeks(week_number, race_name, finalized_at, last_updated, locked)
            VALUES(?, ?, ?, ?, 1)
            ON CONFLICT(week_number) DO UPDATE SET
              race_name=excluded.race_name,
              finalized_at=excluded.finalized_at,
              last_updated=excluded.last_updated,
              locked=1
            """,
            (week, race_name, now, now),
        )

        # Ensure draft picks for this week are no longer "current".
        cur.execute("UPDATE picks SET is_current_pick=0 WHERE week=?", (week,))

        # Update season totals + last-week weeklyPoints + store per-player finish info.
        for player_name, score in score_by_player.items():
            cur.execute("SELECT total_points FROM players WHERE player_name=?", (player_name,))
            row = cur.fetchone()
            old_total = int(row["total_points"]) if row else 0
            new_total = old_total + score.total_week_points

            cur.execute(
                "UPDATE players SET total_points=? WHERE player_name=?",
                (new_total, player_name),
            )
            cur.execute(
                "INSERT OR REPLACE INTO weeklyPoints(player_name, weekly_points) VALUES(?, ?)",
                (player_name, score.total_week_points),
            )
            cur.execute(
                """
                INSERT INTO week_results(
                  week_number, player_name, picked_driver, finish_pos,
                  weekly_points, bonus_points
                )
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(week_number, player_name) DO UPDATE SET
                  picked_driver=excluded.picked_driver,
                  finish_pos=excluded.finish_pos,
                  weekly_points=excluded.weekly_points,
                  bonus_points=excluded.bonus_points
                """,
                (
                    week,
                    player_name,
                    score.picked_driver,
                    score.finish_pos,
                    score.weekly_points,
                    score.bonus_points,
                ),
            )

    return score_by_player


def get_scoreboard_payload(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Produces the JSON shape used by the legacy frontend in `index.html`.
    """
    # Players in exact order used by the legacy script:
    players = sorted(list_players(conn))
    drivers = list_drivers(conn)

    cur = conn.cursor()
    cur.execute("SELECT player_name, driver, MAX(is_current_pick) AS is_current_pick FROM picks GROUP BY player_name, driver")

    picks: Dict[str, Dict[str, bool]] = {}
    for row in cur.fetchall():
        p = row["player_name"]
        d = row["driver"]
        if p not in picks:
            picks[p] = {}
        picks[p][d] = bool(row["is_current_pick"])

    # Season totals
    cur.execute("SELECT player_name, total_points FROM players ORDER BY total_points DESC")
    total_points = [{"player": r["player_name"], "points": r["total_points"]} for r in cur.fetchall()]

    cur.execute("SELECT player_name, weekly_points FROM weeklyPoints ORDER BY weekly_points DESC")
    weekly_points = [{"player": r["player_name"], "points": r["weekly_points"]} for r in cur.fetchall()]

    latest_week = get_latest_finalized_week_number(conn)
    race_name = get_race_name_for_week(conn, latest_week) if latest_week is not None else None

    # Pick order for next race = worst finish -> best finish of the last finalized week.
    sorted_results: List[str] = []
    if latest_week is not None:
        cur.execute(
            """
            SELECT player_name, finish_pos
            FROM week_results
            WHERE week_number=?
            ORDER BY finish_pos ASC
            """,
            (latest_week,),
        )
        rows = cur.fetchall()
        finish_sorted = [(r["player_name"], int(r["finish_pos"])) for r in rows]
        finish_sorted_rev = list(reversed(finish_sorted))
        sorted_results = [p for p, _pos in finish_sorted_rev]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "race_name": race_name or "DBC Picks",
        "last_updated": now,
        "players": players,
        "drivers": drivers,
        "picks": picks,
        "total_points": total_points,
        "weekly_points": weekly_points,
        "sorted_results": sorted_results,
    }

