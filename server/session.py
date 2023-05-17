import random

import redis

import server.config as config
from server.models.game_state import GameBoard, Player

_session_db = redis.StrictRedis(config.REDIS_HOST, int(config.REDIS_PORT), charset="utf-8", decode_responses=True)


_GAME_CODE_CHARACTERS = "BCDFGHJKLMNPQRSTVWXZ"
_GAME_CODE_LENGTH = 4
_SESSION_EXPIRY = 43200  # 12 hours


def _game_board_key(game_id: str):
    return f"{game_id}:board"


def _player_key(game_id: str, player_id: str):
    return f"{game_id}:player:{player_id}"


def _buzz_lock_key(game_id: str, clue_id: str) -> str:
    return f"{game_id}:buzz_lock:{clue_id}"


def _players_buzzed_key(game_id: str, clue_id: str) -> str:
    return f"{game_id}:player_buzz:{clue_id}"


def _player_answered_key(game_id: str, clue_id) -> str:
    return f"{game_id}:player_answered:{clue_id}"


def _all_players_prefix(game_id: str) -> str:
    return f"{game_id}:player:*"


def _host_key(game_id: str) -> str:
    return f"{game_id}:host"


def generate_game_id() -> str:
    code = []
    for _ in range(_GAME_CODE_LENGTH):
        idx = random.randint(0, len(_GAME_CODE_CHARACTERS) - 1)
        code.append(_GAME_CODE_CHARACTERS[idx])
    return "".join(code)


def get_game_board(game_id: str) -> GameBoard:
    raw_record = _session_db.get(_game_board_key(game_id))
    return GameBoard.parse_raw(raw_record)


def save_game_board(game_id: str, game_board: GameBoard) -> None:
    _session_db.set(_game_board_key(game_id), game_board.json(), ex=_SESSION_EXPIRY)


def game_exists(game_id: str) -> bool:
    return _session_db.exists(_game_board_key(game_id)) != 0


def get_player(game_id: str, player_id: str) -> Player:
    record = _session_db.get(_player_key(game_id, player_id))
    return Player.parse_raw(record)


def get_all_players(game_id: str) -> list[Player]:
    keys = [k for k in _session_db.scan_iter(_all_players_prefix(game_id))]
    return [Player.parse_raw(p) for p in _session_db.mget(keys)]


def save_player(game_id: str, player: Player) -> None:
    _session_db.set(_player_key(game_id, player.id), player.json(), ex=_SESSION_EXPIRY)


def remove_player(game_id: str, player_id: str) -> None:
    _session_db.delete(_player_key(game_id, player_id))


def add_player_buzz(game_id: str, clue_id: str, player_id: str) -> None:
    _session_db.sadd(_players_buzzed_key(game_id, clue_id), player_id)
    _session_db.expire(_players_buzzed_key(game_id, clue_id), time=_SESSION_EXPIRY)


def get_players_buzzed(game_id: str, clue_id: str) -> list[str]:
    return _session_db.smembers(_players_buzzed_key(game_id, clue_id))


def check_buzz_lock(game_id: str, clue_id: str) -> int:
    ok = _session_db.incr(_buzz_lock_key(game_id, clue_id)) == 1
    _session_db.expire(_buzz_lock_key(game_id, clue_id), time=_SESSION_EXPIRY)
    return ok


def reset_buzz_lock(game_id: str, clue_id: str) -> None:
    _session_db.set(_buzz_lock_key(game_id, clue_id), 0, ex=_SESSION_EXPIRY)


def save_host(game_id: str) -> None:
    _session_db.set(_host_key(game_id), 1, ex=_SESSION_EXPIRY)


def host_exists(game_id: str) -> bool:
    return _session_db.exists(_host_key(game_id)) != 0
