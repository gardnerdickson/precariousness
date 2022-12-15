import uuid
from typing import Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


player_sockets = {}


class InvalidPlayerId(Exception):
    def __init__(self, player_id):
        self.player_id = player_id


@app.exception_handler(InvalidPlayerId)
async def invalid_player_id_handler(
    initiator: Union[Request, WebSocket], exc: InvalidPlayerId
):
    if isinstance(initiator, WebSocket):
        await initiator.accept()
        await initiator.send_text(
            f"Invalid player ID: {exc.player_id}. Closing websocket."
        )
        await initiator.close()
    else:
        return {"error": f"Invalid player ID: {exc.player_id}"}


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
    return {"id": new_player_id}


@app.websocket("/player_socket/{player_id}")
async def player_socket(websocket: WebSocket, player_id: str):
    if player_id not in player_sockets:
        raise InvalidPlayerId(player_id)
    await websocket.accept()
    player_sockets[player_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            for other_player_id, socket in player_sockets.items():
                if player_id != other_player_id:
                    await socket.send_text("player sent: " + data)
    except WebSocketDisconnect:
        del player_sockets[player_id]


@app.websocket("/host_socket")
async def host_socket(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text("host sent: " + data)


@app.websocket("/gameboard_socket")
async def gameboard_socket(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text("gameboard sent: " + data)
