import json
import logging
import os
import random
import sys
import uuid
from json import JSONDecodeError
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from jsonschema import validate
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import FileResponse

from server.exceptions import InvalidPlayerId, InvalidOperation
from server.handler import SocketHandler
from server.log import configure_logging
from server.models.game_state import GameBoardState, Player
from server.models.message import (
    PlayerBuzzMessage,
    PlayerInitMessage,
    PlayerJoinedMessage,
    PlayerTurnStartMessage,
    StartGameMessage,
    WaitingForPlayerMessage,
    AllPlayersIn,
    Clue,
    SelectClueMessage,
    ClueSelectedMessage,
    CategorySelectedMessage,
    ResponseCorrectMessage,
    ResponseIncorrectMessage,
    ClueAnswered,
    NewRoundMessage,
    GameOverMessage,
    SelectCategoryMessage,
    DeselectCategoryMessage,
    ClueRevealedMessage,
    ClueInfo,
    ClueExpiredMessage,
)

load_dotenv()

configure_logging()
logger = logging.getLogger(__name__)

if "GAME_FILE" not in os.environ:
    raise KeyError("Environment variable 'GAME_FILE' required.")

with open(os.environ["GAME_FILE"]) as data_fh, open("server/game_schema.json") as schema_fh:
    game_data = json.load(data_fh)
    game_schema = json.load(schema_fh)
    validate(game_data, game_schema)
    game_board_state = GameBoardState.parse_obj(game_data)

app = FastAPI(title="Precariousness!")
app.mount("/static", StaticFiles(directory="static"), name="static")

player_sockets: Dict[str, Optional[WebSocket]] = {}
host_socket: Optional[WebSocket] = None
game_board_socket: Optional[WebSocket] = None

players: Dict[str, Player] = {}
current_player_idx = 0
accept_player_buzz = True
players_buzzed = set()


socket_handler = SocketHandler()


@app.exception_handler(InvalidPlayerId)
async def invalid_player_id_handler(_: Request, exc: InvalidPlayerId):
    message = f"Invalid player ID: {exc.player_id}"
    logger.error(message, exc_info=sys.exc_info())
    return {"error": message}


@app.exception_handler(ValidationError)
async def validation_error(_: Request, exc: ValidationError):
    return {"error": f"Bad request: {str(exc)}"}


@app.get("/player")
async def player_init():
    return FileResponse("static/player.html")


@app.get("/host")
async def host_init():
    return FileResponse("static/host.html")


@app.get("/gameboard")
async def gameboard_init():
    return FileResponse("static/gameboard.html")


@app.post("/new_player")
async def register_new_player():
    new_player_id = str(uuid.uuid4())
    player_sockets[new_player_id] = None
    return {"playerId": new_player_id}


@app.post("/get_game_board_state")
async def get_game_board_state():
    return game_board_state


@app.post("/get_players_state")
async def get_players_state():
    return list(players.values())


@app.post("/mark_answer_used")
async def mark_answer_used(tile: Clue):
    categories = game_board_state.rounds[game_board_state.current_round]
    category = next((c for c in categories if c.key == tile.category_key), None)
    if not category:
        raise KeyError(f"Category does not exist: {tile.category_key}")
    category.tiles[tile.amount].answered = True
    logger.info(f"Marked {game_board_state.current_round} -> {tile.category_key} -> {tile.amount} as used")


@app.websocket("/player_socket/{player_id}")
async def init_player_socket(websocket: WebSocket, player_id: str):
    if player_id not in player_sockets:
        raise InvalidPlayerId(player_id)
    await websocket.accept()
    player_sockets[player_id] = websocket
    try:
        while True:
            await socket_handler.handle_operation(websocket, player_id=player_id)
    except WebSocketDisconnect:
        del player_sockets[player_id]


@app.websocket("/host_socket")
async def init_host_socket(websocket: WebSocket):
    await websocket.accept()
    global host_socket
    host_socket = websocket
    try:
        while True:
            await socket_handler.handle_operation(host_socket)
    except WebSocketDisconnect:
        logger.error("Host disconnected")


@app.websocket("/gameboard_socket")
async def init_gameboard_socket(websocket: WebSocket):
    await websocket.accept()
    global game_board_socket
    game_board_socket = websocket
    while True:
        await socket_handler.handle_operation(game_board_socket)


@socket_handler.error(InvalidOperation)
async def handle_invalid_operation(websocket: WebSocket, exc: InvalidOperation):
    message = f"Invalid operation: {exc.operation_name}"
    logger.error(message, exc_info=sys.exc_info())
    await websocket.send_json({"error": message})


@socket_handler.error(ValidationError)
async def handle_validation_error(websocket: WebSocket, exc: ValidationError):
    message = "Invalid message"
    logger.error(message, exc_info=sys.exc_info())
    await websocket.send_json({"error": message})


@socket_handler.error(JSONDecodeError)
async def handle_json_decode_error(websocket: WebSocket, exc: JSONDecodeError):
    message = "Invalid JSON"
    logger.error(message, exc_info=sys.exc_info())
    await websocket.send_json({"error": message})


@socket_handler.error(Exception)
async def handle_exception(websocket: WebSocket, _: Exception):
    message = "Server error"
    logger.error(message, exc_info=sys.exc_info())
    await websocket.send_json({"error": message})


@socket_handler.operation("PLAYER_INIT", PlayerInitMessage)
async def handle_player_init(inbound_message: PlayerInitMessage, player_id: str):
    players[player_id] = Player(id=player_id, name=inbound_message.player_name, score=0)
    logger.info(f"Player initialized: {players[player_id]}")

    outbound_message = PlayerJoinedMessage(player_name=inbound_message.player_name, player_score=0)
    await socket_handler.send_message("PLAYER_JOINED", outbound_message, host_socket)
    await socket_handler.send_message("PLAYER_JOINED", outbound_message, game_board_socket)


@socket_handler.operation("START_GAME", StartGameMessage)
async def handle_start_game(_: StartGameMessage):
    all_players_in_message = AllPlayersIn()
    await socket_handler.send_message("ALL_PLAYERS_IN", all_players_in_message, game_board_socket)
    random_player = list(players.values())[random.randint(0, len(players)) - 1]
    await _next_turn(random_player.id)


@socket_handler.operation("SELECT_CATEGORY", SelectCategoryMessage)
async def handle_category_selected(select_category_message: SelectCategoryMessage, player_id: str):
    category_selected_message = CategorySelectedMessage(category_key=select_category_message.category_key)
    await socket_handler.send_message("CATEGORY_SELECTED", category_selected_message, [host_socket, game_board_socket])


@socket_handler.operation("DESELECT_CATEGORY", DeselectCategoryMessage)
async def handle_deselect_category(deselect_category_message: DeselectCategoryMessage, player_id: str):
    await socket_handler.send_message("CATEGORY_DESELECTED", deselect_category_message, [host_socket, game_board_socket])


@socket_handler.operation("SELECT_CLUE", SelectClueMessage)
async def handle_clue_selected(select_clue_message: SelectClueMessage, player_id: str):
    categories = game_board_state.rounds[game_board_state.current_round]
    category = next((c for c in categories if c.key == select_clue_message.category_key), None)
    if not category:
        raise KeyError(f"Category does not exist: {select_clue_message.category_key}")
    clue_text = category.tiles[select_clue_message.amount].clue
    clue_selected_message = ClueSelectedMessage(clue_text=clue_text, **select_clue_message.dict())
    await socket_handler.send_message("CLUE_SELECTED", clue_selected_message, [host_socket, game_board_socket, *player_sockets.values()])


@socket_handler.operation("CLUE_REVEALED", ClueRevealedMessage)
async def handle_clue_revealed(clue_revealed_message: ClueRevealedMessage):
    tile = game_board_state.get_tile(clue_revealed_message.category_key, clue_revealed_message.amount)
    await socket_handler.send_message(
        "CLUE_REVEALED", ClueInfo(clue=tile.clue, correct_response=tile.correct_response), [host_socket, *player_sockets.values()]
    )


@socket_handler.operation("PLAYER_BUZZ", PlayerBuzzMessage)
async def handle_player_buzz(_: PlayerBuzzMessage, player_id: str):
    player_name = players[player_id].name
    global accept_player_buzz
    if accept_player_buzz and player_id not in players_buzzed:
        logger.info(f"{player_name} was the first to buzz")
        accept_player_buzz = False
        players_buzzed.add(player_id)
        player_buzz_message = PlayerBuzzMessage(player_name=player_name)
        await socket_handler.send_message("PLAYER_BUZZED", player_buzz_message, [host_socket, game_board_socket, *player_sockets.values()])
    else:
        logger.info(f"Player {player_name} buzzed too late.")


@socket_handler.operation("RESPONSE_CORRECT", ResponseCorrectMessage)
async def handle_response_correct(response_correct_message: ResponseCorrectMessage):
    player = next((p for p in players.values() if p.name == response_correct_message.player_name))
    player.score += int(response_correct_message.amount)

    tile = game_board_state.get_tile(response_correct_message.category_key, str(response_correct_message.amount))
    tile.answered = True

    clue_answered_message = ClueAnswered(
        category_key=response_correct_message.category_key, amount=response_correct_message.amount, answered_correctly=True, player_name=player.name
    )
    await socket_handler.send_message("CLUE_ANSWERED", clue_answered_message, [host_socket, game_board_socket, *player_sockets.values()])
    await socket_handler.send_message("TURN_OVER", clue_answered_message, [host_socket, game_board_socket, *player_sockets.values()])
    await socket_handler.send_message("PLAYER_STATE_CHANGED", list(players.values()), [host_socket, game_board_socket, *player_sockets.values()])

    remaining_tiles = game_board_state.get_remaining_tiles()
    if len(remaining_tiles) == 0:
        await _next_round()
    await _next_turn(player.id)


@socket_handler.operation("RESPONSE_INCORRECT", ResponseIncorrectMessage)
async def handle_response_incorrect(response_incorrect_message: ResponseIncorrectMessage):
    player = next((p for p in players.values() if p.name == response_incorrect_message.player_name))
    player.score -= int(response_incorrect_message.amount)
    global accept_player_buzz
    accept_player_buzz = True

    tile = game_board_state.get_tile(response_incorrect_message.category_key, str(response_incorrect_message.amount))
    tile.answered = True

    clue_answered_message = ClueAnswered(
        category_key=response_incorrect_message.category_key, amount=response_incorrect_message.amount, answered_correctly=False, player_name=player.name
    )
    await socket_handler.send_message("CLUE_ANSWERED", clue_answered_message, [host_socket, game_board_socket, *player_sockets.values()])
    await socket_handler.send_message("PLAYER_STATE_CHANGED", list(players.values()), [host_socket, game_board_socket, *player_sockets.values()])

    if len(players_buzzed) == len(players):
        await socket_handler.send_message("TURN_OVER", clue_answered_message, [host_socket, game_board_socket, *player_sockets.values()])
        next_player = get_next_player_when_clue_not_answered_correctly()
        await _next_turn(next_player.id)


@socket_handler.operation("CLUE_EXPIRED", ClueExpiredMessage)
async def handle_clue_expired(clue_expired_message: ClueExpiredMessage):
    tile = game_board_state.get_tile(clue_expired_message.category_key, clue_expired_message.amount)
    tile.answered = True

    clue_answered_message = ClueAnswered(category_key=clue_expired_message.category_key, amount=clue_expired_message.amount, answered_correctly=False)
    await socket_handler.send_message("CLUE_ANSWERED", clue_answered_message, [host_socket, game_board_socket, *player_sockets.values()])
    await socket_handler.send_message("TURN_OVER", clue_answered_message, [host_socket, game_board_socket, *player_sockets.values()])

    remaining_tiles = game_board_state.get_remaining_tiles()
    if len(remaining_tiles) == 0:
        await _next_round()

    next_player = get_next_player_when_clue_not_answered_correctly()
    await _next_turn(next_player.id)


def get_next_player_when_clue_not_answered_correctly() -> Player:
    sorted_by_amount = sorted(players.values(), key=lambda p: p.score)
    return sorted_by_amount[0]


async def _next_turn(player_id: str):
    global accept_player_buzz, players_buzzed
    accept_player_buzz = True
    players_buzzed = set()

    current_player = players[player_id]
    waiting_for_player_message = WaitingForPlayerMessage(player_name=current_player.name)
    await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, [host_socket, game_board_socket])
    for player_id, socket in player_sockets.items():
        if player_id == current_player.id:
            await socket_handler.send_message("PLAYER_TURN_START", PlayerTurnStartMessage(), socket)
        else:
            await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, socket)


async def _next_round():
    game_board_state.current_round += 1

    if game_board_state.current_round >= len(game_board_state.rounds):
        logger.debug("Game over")
        await socket_handler.send_message(
            "GAME_OVER", GameOverMessage(players=list(players.values())), [host_socket, game_board_socket, *player_sockets.values()]
        )
    else:
        logger.debug(f"New round: {game_board_state.current_round}")
        await socket_handler.send_message("NEW_ROUND", NewRoundMessage(), game_board_socket)
