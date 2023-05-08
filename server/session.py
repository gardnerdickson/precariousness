import random
from typing import List

import redis

from server.models.game_state import GameBoard, Player

_session_db = redis.StrictRedis("localhost", 6379, charset="utf-8", decode_responses=True)


_GAME_CODE_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_GAME_CODE_LENGTH = 4


def _game_board_key(game_id: str):
    return f"{game_id}:board"


def _player_key(game_id: str, player_id: str):
    return f"{game_id}:player:{player_id}"


def _all_players_prefix(game_id: str):
    return f"{game_id}:player:*"


def _host_key(game_id: str):
    return f"{game_id}:host"


def generate_game_id():
    code = []
    for _ in range(_GAME_CODE_LENGTH):
        idx = random.randint(0, len(_GAME_CODE_CHARACTERS) - 1)
        code.append(_GAME_CODE_CHARACTERS[idx])
    return "".join(code)


def get_game_board(game_id: str) -> GameBoard:
    raw_record = _session_db.get(_game_board_key(game_id))
    return GameBoard.parse_raw(raw_record)


def save_game_board(game_id: str, game_board: GameBoard) -> None:
    _session_db.set(_game_board_key(game_id), game_board.json())


def game_exists(game_id: str) -> bool:
    return _session_db.exists(_game_board_key(game_id)) != 0


def get_player(game_id: str, player_id: str) -> Player:
    record = _session_db.get(_player_key(game_id, player_id))
    return Player.parse_raw(record)


def get_all_players(game_id: str) -> List[Player]:
    keys = [k for k in _session_db.scan_iter(_all_players_prefix(game_id))]
    return [Player.parse_raw(p) for p in _session_db.mget(keys)]


def save_player(game_id: str, player: Player) -> None:
    _session_db.set(_player_key(game_id, player.id), player.json())


def save_host(game_id: str) -> None:
    _session_db.set(_host_key(game_id), 1)


def host_exists(game_id: str) -> bool:
    return _session_db.exists(_host_key(game_id)) != 0
