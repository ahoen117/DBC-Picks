from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple


@dataclass(frozen=True)
class WeeklyScore:
    player: str
    picked_driver: str
    finish_pos: int
    weekly_points: int
    bonus_points: int
    total_week_points: int


def extract_event_short_name(scoreboard_json: Mapping[str, Any]) -> str:
    """
    ESPN scoreboard payload shape:
      events[0].shortName
    """
    return scoreboard_json["events"][0]["shortName"]


def extract_positions_by_last_name(scoreboard_json: Mapping[str, Any]) -> Dict[str, int]:
    """
    Builds a map of driver last name -> finishing order.

    Note: this intentionally matches the legacy behavior:
    - use athlete.fullName
    - if last token is "Jr.", use the token before it
    """
    competitors = scoreboard_json["events"][0]["competitions"][0]["competitors"]

    positions: Dict[str, int] = {}
    for competitor in competitors:
        full_name = competitor["athlete"]["fullName"]
        pos = int(competitor["order"])

        last_parts = full_name.split()
        last_name = last_parts[-1]
        if last_name == "Jr." and len(last_parts) >= 2:
            last_name = last_parts[-2]

        positions[last_name] = pos

    return positions


def compute_week_results(
    *,
    players_to_picks: Mapping[str, str],
    positions_by_last_name: Mapping[str, int],
) -> Tuple[List[Tuple[str, int]], Dict[str, WeeklyScore], List[str]]:
    """
    Returns:
      sorted_results: list of (player, finish_pos) sorted best (lowest pos) -> worst
      score_by_player: detailed per-player weekly scoring
      next_pick_order: list of players worst -> best (the same order the legacy site shows)
    """
    # Legacy: always award base points based on finish ordering and add +1 bonus for winner.
    n = len(players_to_picks)

    weekly_points_by_player: Dict[str, int] = {}
    bonus_by_player: Dict[str, int] = {}
    finish_pos_by_player: Dict[str, int] = {}

    for player, picked_driver_last_name in players_to_picks.items():
        finish_pos = positions_by_last_name.get(picked_driver_last_name, 999)
        finish_pos_by_player[player] = finish_pos

    sorted_results = sorted(
        [(player, finish_pos_by_player[player]) for player in players_to_picks.keys()],
        key=lambda x: x[1],
    )

    score_by_player: Dict[str, WeeklyScore] = {}

    for rank_index, (player, finish_pos) in enumerate(sorted_results):
        # Legacy behavior: with 9 players, points start at 8 for best finisher.
        base_points = (n - 1) - rank_index
        bonus_points = 1 if finish_pos == 1 else 0

        if finish_pos == 999:
            # Legacy behavior: unmatched driver yields 0 points and still shows finish=999.
            base_points = 0
            bonus_points = 0

        weekly_points = base_points + bonus_points
        weekly_points_by_player[player] = weekly_points
        bonus_by_player[player] = bonus_points

        score_by_player[player] = WeeklyScore(
            player=player,
            picked_driver=players_to_picks[player],
            finish_pos=finish_pos,
            weekly_points=weekly_points,
            bonus_points=bonus_points,
            total_week_points=weekly_points,
        )

    next_pick_order = [player for player, _pos in reversed(sorted_results)]

    return sorted_results, score_by_player, next_pick_order


def format_spelling_warnings(score_by_player: Mapping[str, WeeklyScore]) -> List[str]:
    warnings: List[str] = []
    for player, score in score_by_player.items():
        if score.finish_pos == 999:
            warnings.append(f"{player}: check spelling for {score.picked_driver}")
    return warnings

