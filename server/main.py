import uuid
from typing import Union, Dict, Optional, Type, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError, BaseModel
from starlette.requests import Request
from starlette.responses import FileResponse

from server.model import PlayerInitMessage, SocketMessage, Player, PlayerBuzzMessage

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

player_sockets: Dict[str, Optional[WebSocket]] = {}
host_socket: Optional[WebSocket] = None
gameboard_socket: Optional[WebSocket] = None

players: Dict[str, Player] = {}


class Handler:

    def __init__(self):
        self.handlers = {}

    def __call__(self, operation_name: str, model_type: Type[BaseModel]):
        if operation_name in self.handlers:
            raise KeyError(f"Operation name '{operation_name}' already in use")

        def decorator(func):
            self.handlers[operation_name] = (func, model_type)
        return decorator

    def route_message(self, message: Dict[str, Any], **kwargs):
        message = SocketMessage.parse_obj(message)
        if message.operation not in self.handlers:
            raise InvalidOperation(message.operation)
        func, model_type = self.handlers[message.operation]
        payload = model_type.parse_obj(message.payload)
        return func(payload, **kwargs)


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
        await initiator.send_text(
            f"Invalid player ID: {exc.player_id}. Closing websocket."
        )
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
            handler.route_message(message, player_id=player_id)
    except WebSocketDisconnect:
        del player_sockets[player_id]


@app.websocket("/host_socket")
async def init_host_socket(websocket: WebSocket):
    await websocket.accept()
    global host_socket
    host_socket = websocket
    while True:
        data = await websocket.receive_text()
        for player_id, socket in player_sockets.items():
            await socket.send_text(f"message from player: {data}")


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
def handle_player_init(message: PlayerInitMessage, player_id: str):
    players[player_id] = Player(player_id, message.player_name, 0)
    print(f"Player initialized: {players[player_id]}")


@handler("PLAYER_BUZZ", PlayerBuzzMessage)
def handle_player_buzz(_: PlayerBuzzMessage, player_id: str):
    print(f"Player {player_id} buzzed!!")
