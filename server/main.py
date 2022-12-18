import random
import uuid
from typing import Any, Dict, Optional, Type, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import FileResponse

from server.model import (
    Player,
    PlayerBuzzMessage,
    PlayerInitMessage,
    PlayerJoinedMessage,
    PlayerTurnStartMessage,
    PrecariousnessBaseModel,
    SocketMessage,
    StartGameMessage,
    WaitingForPlayerMessage,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

player_sockets: Dict[str, Optional[WebSocket]] = {}
host_socket: Optional[WebSocket] = None
gameboard_socket: Optional[WebSocket] = None

players: Dict[str, Player] = {}
current_player_idx = 0


class Handler:
    def __init__(self):
        self.handlers = {}

    def __call__(self, operation_name: str, model_type: Type[PrecariousnessBaseModel]):
        if operation_name in self.handlers:
            raise KeyError(f"Operation name '{operation_name}' already in use")

        def decorator(func):
            self.handlers[operation_name] = (func, model_type)

        return decorator

    async def route_message(self, message: Dict[str, Any], **kwargs):
        message = SocketMessage.parse_obj(message)
        if message.operation not in self.handlers:
            raise InvalidOperation(message.operation)
        func, model_type = self.handlers[message.operation]
        payload = model_type.parse_obj(message.payload)
        return await func(payload, **kwargs)


handler = Handler()


class InvalidPlayerId(Exception):
    def __init__(self, player_id):
        self.player_id = player_id


class InvalidOperation(Exception):
    def __init__(self, operation_name: str):
        self.operation_name = operation_name


@app.exception_handler(InvalidPlayerId)
async def invalid_player_id_handler(initiator: Union[Request, WebSocket], exc: InvalidPlayerId):
    if isinstance(initiator, WebSocket):
        await initiator.accept()
        await initiator.send_text(f"Invalid player ID: {exc.player_id}. Closing websocket.")
        await initiator.close()
    else:
        return {"error": f"Invalid player ID: {exc.player_id}"}


@app.exception_handler(ValidationError)
async def validation_error(initiator: Union[Request, WebSocket], exc: ValidationError):
    error = {"error": f"Bad request: {str(exc)}"}
    if isinstance(initiator, WebSocket):
        await initiator.send_json(error)
    else:
        return error


@app.exception_handler(InvalidOperation)
async def invalid_operation(initiator: WebSocket, exc: InvalidOperation):
    await initiator.send_json({"error": f"Bad request: {str(exc)}"})


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
            message = await websocket.receive_json()
            await handler.route_message(message, player_id=player_id)
    except WebSocketDisconnect:
        del player_sockets[player_id]


@app.websocket("/host_socket")
async def init_host_socket(websocket: WebSocket):
    await websocket.accept()
    global host_socket
    host_socket = websocket
    try:
        while True:
            message = await websocket.receive_json()
            await handler.route_message(message)
    except WebSocketDisconnect:
        print("Host disconnected")


@app.websocket("/gameboard_socket")
async def init_gameboard_socket(websocket: WebSocket):
    await websocket.accept()
    global gameboard_socket
    gameboard_socket = websocket
    while True:
        data = await websocket.receive_text()
        for player_id, socket in player_sockets.items():
            await socket.send_text(f"message from player: {data}")


@handler("PLAYER_INIT", PlayerInitMessage)
async def handle_player_init(inbound_message: PlayerInitMessage, player_id: str):
    players[player_id] = Player(player_id, inbound_message.player_name, 0)
    print(f"Player initialized: {players[player_id]}")

    outbound_message = PlayerJoinedMessage(player_name=inbound_message.player_name, player_score=0)
    await _send_socket_message("PLAYER_JOINED", outbound_message, host_socket)
    await _send_socket_message("PLAYER_JOINED", outbound_message, gameboard_socket)


@handler("START_GAME", StartGameMessage)
async def handle_start_game(_: StartGameMessage):
    # Shuffle turn order
    player_sequence = list(players.values())
    random.shuffle(player_sequence)
    current_player = player_sequence[current_player_idx]

    waiting_for_player_message = WaitingForPlayerMessage(player_name=current_player.name)
    await _send_socket_message("START_GAME", StartGameMessage(), gameboard_socket)
    await _send_socket_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, gameboard_socket)
    await _send_socket_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, host_socket)
    for player_id, socket in player_sockets.items():
        print("iterating on player_id: " + player_id)
        if player_id == current_player.id:
            await _send_socket_message("PLAYER_TURN_START", PlayerTurnStartMessage(), socket)
        else:
            await _send_socket_message("WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, socket)


@handler("PLAYER_BUZZ", PlayerBuzzMessage)
async def handle_player_buzz(_: PlayerBuzzMessage, player_id: str):
    print(f"Player {player_id} buzzed!!")


async def _send_socket_message(operation: str, message: PrecariousnessBaseModel, socket: WebSocket):
    message = SocketMessage(operation=operation, payload=message.dict(by_alias=True))
    await socket.send_json(message.dict(by_alias=True))
