import random
import uuid
from json import JSONDecodeError
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import FileResponse

from server.exceptions import InvalidPlayerId, InvalidOperation
from server.handler import SocketHandler
from server.model import (
    Player,
    PlayerBuzzMessage,
    PlayerInitMessage,
    PlayerJoinedMessage,
    PlayerTurnStartMessage,
    StartGameMessage,
    WaitingForPlayerMessage, )

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
    return {"error": f"Invalid player ID: {exc.player_id}"}


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
        print("Host disconnected")


@app.websocket("/gameboard_socket")
async def init_gameboard_socket(websocket: WebSocket):
    await websocket.accept()
    global gameboard_socket
    gameboard_socket = websocket
    while True:
        await socket_handler.handle_operation(gameboard_socket)


@socket_handler.error(InvalidOperation)
async def handle_invalid_operation(websocket: WebSocket, exc: InvalidOperation):
    await websocket.send_json({"error": f"Invalid operation: {exc.operation_name}"})


@socket_handler.error(ValidationError)
async def handle_validation_error(websocket: WebSocket, exc: ValidationError):
    await websocket.send_json({"error": "Invalid message"})


@socket_handler.error(JSONDecodeError)
async def handle_json_decode_error(websocket: WebSocket, exc: JSONDecodeError):
    await websocket.send_json({"error": "Invalid JSON"})


@socket_handler.error(Exception)
async def handle_exception(websocket: WebSocket, _: Exception):
    await websocket.send_json({"error": "Server error"})


@socket_handler.operation("PLAYER_INIT", PlayerInitMessage)
async def handle_player_init(inbound_message: PlayerInitMessage, player_id: str):
    players[player_id] = Player(player_id, inbound_message.player_name, 0)
    print(f"Player initialized: {players[player_id]}")

    outbound_message = PlayerJoinedMessage(player_name=inbound_message.player_name, player_score=0)
    await socket_handler.send_message("PLAYER_JOINED", outbound_message, host_socket)
    await socket_handler.send_message("PLAYER_JOINED", outbound_message, gameboard_socket)


@socket_handler.operation("START_GAME", StartGameMessage)
async def handle_start_game(_: StartGameMessage):
    # Shuffle turn order
    player_sequence = list(players.values())
    random.shuffle(player_sequence)
    current_player = player_sequence[current_player_idx]

    waiting_for_player_message = WaitingForPlayerMessage(player_name=current_player.name)
    await socket_handler.send_message("START_GAME", StartGameMessage(), gameboard_socket)
    await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, gameboard_socket)
    await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, host_socket)
    for player_id, socket in player_sockets.items():
        print("iterating on player_id: " + player_id)
        if player_id == current_player.id:
            await socket_handler.send_message("PLAYER_TURN_START", PlayerTurnStartMessage(), socket)
        else:
            await socket_handler.send_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, socket)


@socket_handler.operation("PLAYER_BUZZ", PlayerBuzzMessage)
async def handle_player_buzz(_: PlayerBuzzMessage, player_id: str):
    print(f"Player {player_id} buzzed!!")
