from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/player")
async def player_init():
    return FileResponse("static/player.html")


@app.get("/host")
async def host_init():
    return FileResponse("static/host.html")


@app.get("/gameboard")
async def gameboard_init():
    return FileResponse("static/gameboard.html")


@app.websocket("/player_socket")
async def player_socket(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text("player sent: " + data)


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


