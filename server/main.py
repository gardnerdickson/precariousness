import json
import logging
import os
import random
import sys
import uuid
from collections import OrderedDict
from json import JSONDecodeError
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import FileResponse

from server.log import configure_logging
from server.exceptions import InvalidPlayerId, InvalidOperation
from server.handler import SocketHandler
from server.model import (
    Player,
    PlayerBuzzMessage,
    PlayerInitMessage,
    PlayerJoinedMessage,
    PlayerTurnStartMessage,
    StartGameMessage,
    WaitingForPlayerMessage,
    GameBoardState,
    LoadGameBoardMessage,
    Answer,
    SelectQuestionMessage,
    QuestionSelectedMessage,
    DeselectQuestionMessage,
    CategorySelectedMessage,
    QuestionCorrectMessage,
    QuestionIncorrectMessage,
    QuestionAnswered,
)

load_dotenv()

configure_logging()
logger = logging.getLogger(__name__)

if "GAME_FILE" not in os.environ:
    raise KeyError("Environment variable 'GAME_FILE' required.")

with open(os.environ["GAME_FILE"]) as fh:
    game_board_state = GameBoardState.parse_obj(json.load(fh))

app = FastAPI(title="Precariousness!")
app.mount("/static", StaticFiles(directory="static"), name="static")

player_sockets: Dict[str, Optional[WebSocket]] = {}
host_socket: Optional[WebSocket] = None
gameboard_socket: Optional[WebSocket] = None

players: Dict[str, Player] = {}
current_player_idx = 0

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


@app.post("/get_gameboard")
async def get_gameboard():
    return game_board_state


@app.post("/mark_answer_used")
async def mark_answer_used(tile: Answer):
    categories = game_board_state.rounds[game_board_state.current_round].categories
    category = next((c for c in categories if c.name == tile.category), None)
    if not category:
        raise KeyError(f"Category does not exist: {tile.category}")
    category.questions[tile.amount].used = True
    logger.info(f"Marked {game_board_state.current_round} -> {tile.category} -> {tile.amount} as used")


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
    global gameboard_socket
    gameboard_socket = websocket
    while True:
        await socket_handler.handle_operation(gameboard_socket)


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
    await socket_handler.send_message("PLAYER_JOINED", outbound_message, gameboard_socket)


@socket_handler.operation("START_GAME", StartGameMessage)
async def handle_start_game(_: StartGameMessage):
    # Shuffle turn order
    global players
    player_items = list(players.items())
    random.shuffle(player_items)
    players = OrderedDict(player_items)

    load_game_board_message = LoadGameBoardMessage(game_board=game_board_state)
    await socket_handler.send_message("LOAD_GAME_BOARD", load_game_board_message, gameboard_socket)
    await _next_turn()


@socket_handler.operation("SELECT_CATEGORY", SelectQuestionMessage)
async def handle_category_selected(select_category_message: SelectQuestionMessage, player_id: str):
    category_selected_message = CategorySelectedMessage(category=select_category_message.category)
    await socket_handler.send_message("CATEGORY_SELECTED", category_selected_message, [host_socket, gameboard_socket])


@socket_handler.operation("DESELECT_CATEGORY", DeselectQuestionMessage)
async def handle_deselect_category(deselect_category_message: DeselectQuestionMessage, player_id: str):
    await socket_handler.send_message("CATEGORY_DESELECTED", deselect_category_message, [host_socket, gameboard_socket])


@socket_handler.operation("SELECT_QUESTION", SelectQuestionMessage)
async def handle_question_selected(select_question_message: SelectQuestionMessage, player_id: str):
    categories = game_board_state.rounds[game_board_state.current_round].categories
    category = next((c for c in categories if c.name == select_question_message.category), None)
    if not category:
        raise KeyError(f"Category does not exist: {select_question_message.category}")
    answer_text = category.questions[select_question_message.amount].answer
    question_selected_message = QuestionSelectedMessage(answer_text=answer_text, **select_question_message.dict())
    await socket_handler.send_message("QUESTION_SELECTED", question_selected_message, [host_socket, gameboard_socket, *player_sockets.values()])


player_buzzed = None


@socket_handler.operation("PLAYER_BUZZ", PlayerBuzzMessage)
async def handle_player_buzz(_: PlayerBuzzMessage, player_id: str):
    player_name = players[player_id].name
    global player_buzzed
    if player_buzzed is None:
        logger.info(f"{player_name} was the first to buzz")
        player_buzzed = player_id
        player_buzz_message = PlayerBuzzMessage(player_name=player_name)
        await socket_handler.send_message("PLAYER_BUZZED", player_buzz_message, [host_socket, *player_sockets.values()])
    else:
        logger.info(f"Player {player_name} buzzed too late.")


@socket_handler.operation("QUESTION_CORRECT", QuestionCorrectMessage)
async def handle_question_correct(question_correct_message: QuestionCorrectMessage):
    player = next((p for p in players.values() if p.name == question_correct_message.player_name))
    player.score += question_correct_message.amount
    global player_buzzed
    player_buzzed = None

    categories = game_board_state.rounds[game_board_state.current_round].categories
    category = next((c for c in categories if c.name == question_correct_message.category), None)
    if not category:
        raise KeyError(f"Category does not exist: {question_correct_message.category}")
    category.questions[str(question_correct_message.amount)].answered = True

    question_answered_message = QuestionAnswered(category=question_correct_message.category, amount=question_correct_message.amount)
    await socket_handler.send_message("QUESTION_ANSWERED", question_answered_message, [host_socket, gameboard_socket, *player_sockets.values()])
    await socket_handler.send_message("PLAYER_STATE_CHANGED", list(players.values()), [host_socket, gameboard_socket, *player_sockets.values()])
    await _next_turn()


@socket_handler.operation("QUESTION_INCORRECT", QuestionIncorrectMessage)
async def handle_question_incorrect(question_incorrect_message: QuestionIncorrectMessage):
    player = next((p for p in players.values() if p.name == question_incorrect_message.player_name))
    player.score -= question_incorrect_message.amount
    global player_buzzed
    player_buzzed = None

    categories = game_board_state.rounds[game_board_state.current_round].categories
    category = next((c for c in categories if c.name == question_incorrect_message.category), None)
    if not category:
        raise KeyError(f"Category does not exist: {question_incorrect_message.category}")
    category.questions[str(question_incorrect_message.amount)].answered = True

    question_answered_message = QuestionAnswered(category=question_incorrect_message.category, amount=question_incorrect_message.amount)
    await socket_handler.send_message("QUESTION_ANSWERED", question_answered_message, [host_socket, gameboard_socket, *player_sockets.values()])
    await socket_handler.send_message("PLAYER_STATE_CHANGED", list(players.values()), [host_socket, gameboard_socket, *player_sockets.values()])
    await _next_turn()


async def _next_turn():
    global current_player_idx
    player_sequence = list(players.values())
    current_player_idx = (current_player_idx + 1) % len(players)
    current_player = player_sequence[current_player_idx]
    waiting_for_player_message = WaitingForPlayerMessage(player_name=current_player.name)
    await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, [host_socket, gameboard_socket])
    for player_id, socket in player_sockets.items():
        if player_id == current_player.id:
            await socket_handler.send_message("PLAYER_TURN_START", PlayerTurnStartMessage(), socket)
        else:
            await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, socket)
