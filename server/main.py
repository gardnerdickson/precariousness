import json
import logging
import random
import sys
import uuid
from json import JSONDecodeError

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jsonschema import validate
from pydantic import ValidationError

import server.config as config
import server.session as session
from server.exceptions import InvalidPlayerId, InvalidOperation
from server.log import configure_logging
from server.models.game_state import GameBoard, Player
from server.models.message import (
    PlayerBuzzMessage,
    PlayerInitMessage,
    PlayerJoinedMessage,
    PlayerTurnStartMessage,
    StartGameMessage,
    WaitingForPlayerMessage,
    AllPlayersIn,
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
    GameId,
    ClueWithGameId,
)
from server.socket_handler import SocketHandler, register_socket_route, player_channel, host_channel, gameboard_channel, publish_message, \
    unregister_socket_route

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Precariousness!")
app.mount("/static", StaticFiles(directory="static"), name="static")

socket_handler = SocketHandler()


class RequestError(Exception):
    def __init__(self, message: str, status_code=500):
        self.message = message
        self.status_code = status_code

    def __repr__(self):
        return self.message

    def __str__(self):
        return repr(self)

    def to_json_response(self):
        return JSONResponse(status_code=self.status_code, content={"error": self.message})


@app.exception_handler(InvalidPlayerId)
async def invalid_player_id_handler(_: Request, exc: InvalidPlayerId):
    message = f"Invalid player ID: {exc.player_id}"
    logger.error(message, exc_info=sys.exc_info())
    return {"error": message}


@app.exception_handler(ValidationError)
async def validation_error(_: Request, exc: ValidationError):
    return {"error": f"Bad request: {str(exc)}"}


@app.exception_handler(RequestError)
async def bad_request(_: Request, exc: RequestError):
    return exc.to_json_response()


@app.get("/player")
async def player_init():
    return FileResponse("static/player.html")


@app.get("/host")
async def host_init():
    return FileResponse("static/host.html")


@app.get("/gameboard")
async def gameboard_init():
    return FileResponse("static/gameboard.html")


@app.post("/init_game")
async def initialize_game():
    with open(config.GAME_FILE) as data_fh, open("server/game_schema.json") as schema_fh:
        game_data = json.load(data_fh)
        game_schema = json.load(schema_fh)
        validate(game_data, game_schema)
        game_board = GameBoard.parse_obj(game_data)
        game_id = session.generate_game_id()
        session.save_game_board(game_id, game_board)

    response = JSONResponse(content={"gameId": game_id})
    response.set_cookie("game-id", game_id)
    return response


@app.post("/new_player")
async def register_new_player(game_id_request: GameId):
    if not session.game_exists(game_id_request.game_id):
        raise RequestError(status_code=400, message=f"Game ID \"{game_id_request.game_id}\" does not exist")

    new_player_id = str(uuid.uuid4())
    response = JSONResponse(content={"playerId": new_player_id})
    response.set_cookie("game-id", game_id_request.game_id)
    return response


@app.post("/new_host")
async def register_host(game_id_request: GameId):
    if not session.game_exists(game_id_request.game_id):
        raise RequestError(status_code=400, message=f"Game ID \"{game_id_request.game_id}\" does not exist")
    if session.host_exists(game_id_request.game_id):
        raise RequestError(status_code=400, message=f"A host for game ID \"{game_id_request.game_id}\" already exists")
    session.save_host(game_id_request.game_id)

    players = session.get_all_players(game_id_request.game_id)
    response = JSONResponse(content=[p.dict(by_alias=True) for p in players])
    response.set_cookie("game-id", game_id_request.game_id)
    return response


@app.post("/get_game_board_state")
async def get_game_board_state(game_id_request: GameId):
    return session.get_game_board(game_id_request.game_id)


@app.post("/get_players_state")
async def get_players_state(game_id_request: GameId):
    return session.get_all_players(game_id_request.game_id)


@app.post("/mark_answer_used")
async def mark_answer_used(tile: ClueWithGameId):
    game_board = session.get_game_board(tile.game_id)
    categories = game_board.rounds[game_board.current_round]
    category = next((c for c in categories if c.key == tile.category_key), None)
    if not category:
        raise KeyError(f"Category does not exist: {tile.category_key}")
    category.tiles[tile.amount].answered = True
    logger.info(f"Marked {game_board.current_round} -> {tile.category_key} -> {tile.amount} as used")
    session.save_game_board(tile.game_id, game_board)


@app.websocket("/player_socket/{game_id}/{player_id}")
async def init_player_socket(websocket: WebSocket, game_id, player_id: str):
    await websocket.accept()
    await register_socket_route(player_channel(game_id, player_id), websocket)
    await socket_handler.handle_operation(websocket, player_id=player_id)


@app.websocket("/host_socket/{game_id}")
async def init_host_socket(websocket: WebSocket, game_id: str):
    await websocket.accept()
    await register_socket_route(host_channel(game_id), websocket)
    await socket_handler.handle_operation(websocket)


@app.websocket("/gameboard_socket/{game_id}")
async def init_gameboard_socket(websocket: WebSocket, game_id: str):
    await websocket.accept()
    await register_socket_route(gameboard_channel(game_id), websocket)
    await socket_handler.handle_operation(websocket)


@socket_handler.error(InvalidOperation)
async def handle_invalid_operation(websocket: WebSocket, exc: InvalidOperation):
    message = f"Invalid operation: {exc.operation_name}"
    logger.error(message, exc_info=sys.exc_info())
    return message


@socket_handler.error(ValidationError)
async def handle_validation_error(websocket: WebSocket, exc: ValidationError):
    message = "Invalid message"
    logger.error(message, exc_info=sys.exc_info())
    return message


@socket_handler.error(JSONDecodeError)
async def handle_json_decode_error(websocket: WebSocket, exc: JSONDecodeError):
    message = "Invalid JSON"
    logger.error(message, exc_info=sys.exc_info())
    return message


@socket_handler.error(WebSocketDisconnect)
async def handle_websocket_disconnect(websocket: WebSocket, exc: WebSocketDisconnect):
    game_id = websocket.path_params["game_id"]
    if "player_id" in websocket.path_params:
        player_id = websocket.path_params["player_id"]
        session.remove_player(game_id, player_id)
        await unregister_socket_route(player_channel(game_id, player_id))
        logger.warning(f"Player socket \"{player_id}\" disconnected")
    elif websocket.url.path.startswith("/host_socket"):
        await unregister_socket_route(host_channel(game_id))
        logger.error("Host socket disconnected")
    else:
        await unregister_socket_route(gameboard_channel(game_id))
        logger.error("Gameboard socket disconnected")

    return None


@socket_handler.error(Exception)
async def handle_exception(websocket: WebSocket, _: Exception):
    message = "Server error"
    logger.error(message, exc_info=sys.exc_info())
    return message


@socket_handler.operation("PLAYER_INIT", PlayerInitMessage)
async def handle_player_init(game_id: str, inbound_message: PlayerInitMessage, player_id: str):
    new_player = Player(id=player_id, name=inbound_message.player_name, score=0)
    session.save_player(game_id, new_player)
    logger.info(f"Player initialized: ({new_player.name}){player_id}")
    outbound_message = PlayerJoinedMessage(player_id=player_id, player_name=inbound_message.player_name, player_score=0)
    await publish_message(game_id, "PLAYER_JOINED", outbound_message, [host_channel(game_id), gameboard_channel(game_id)])


@socket_handler.operation("START_GAME", StartGameMessage)
async def handle_start_game(game_id: str, _: StartGameMessage):
    all_players_in_message = AllPlayersIn()
    await publish_message(game_id, "ALL_PLAYERS_IN", all_players_in_message, gameboard_channel(game_id))
    players = session.get_all_players(game_id)
    random_player = list(players)[random.randint(0, len(players)) - 1]
    await _next_turn(random_player, game_id)


@socket_handler.operation("SELECT_CATEGORY", SelectCategoryMessage)
async def handle_category_selected(game_id: str, select_category_message: SelectCategoryMessage, player_id: str):
    category_selected_message = CategorySelectedMessage(category_key=select_category_message.category_key)
    await publish_message(game_id, "CATEGORY_SELECTED", category_selected_message, [host_channel(game_id), gameboard_channel(game_id)])


@socket_handler.operation("DESELECT_CATEGORY", DeselectCategoryMessage)
async def handle_deselect_category(game_id: str, deselect_category_message: DeselectCategoryMessage, player_id: str):
    await publish_message(game_id, "CATEGORY_DESELECTED", deselect_category_message, [host_channel(game_id), gameboard_channel(game_id)])


@socket_handler.operation("SELECT_CLUE", SelectClueMessage)
async def handle_clue_selected(game_id: str, select_clue_message: SelectClueMessage, player_id: str):
    game_board = session.get_game_board(game_id)
    categories = game_board.rounds[game_board.current_round]
    category = next((c for c in categories if c.key == select_clue_message.category_key), None)
    if not category:
        raise KeyError(f"Category does not exist: {select_clue_message.category_key}")
    clue_text = category.tiles[select_clue_message.amount].clue
    clue_selected_message = ClueSelectedMessage(clue_text=clue_text, **select_clue_message.dict())

    player_ids = [p.id for p in session.get_all_players(game_id)]
    await publish_message(
        game_id,
        "CLUE_SELECTED",
        clue_selected_message,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )


@socket_handler.operation("CLUE_REVEALED", ClueRevealedMessage)
async def handle_clue_revealed(game_id: str, clue_revealed_message: ClueRevealedMessage):
    print("Inside CLUE_REVEALED handler")
    game_board = session.get_game_board(game_id)
    tile = game_board.get_tile(clue_revealed_message.category_key, clue_revealed_message.amount)

    clue_info_message = ClueInfo(clue=tile.clue, correct_response=tile.correct_response, clue_id=tile.id)
    player_ids = [p.id for p in session.get_all_players(game_id)]
    print("Sending CLUE_REVEALED message to host and players: ", player_ids)
    await publish_message(game_id, "CLUE_REVEALED", clue_info_message, [host_channel(game_id), *player_channel(game_id, player_ids)])


@socket_handler.operation("PLAYER_BUZZ", PlayerBuzzMessage)
async def handle_player_buzz(game_id: str, buzz_message: PlayerBuzzMessage, player_id: str):
    clue_id = buzz_message.clue_id
    if session.check_buzz_lock(game_id, clue_id):
        session.add_player_buzz(game_id, clue_id, player_id)
        player_buzz_message = PlayerBuzzMessage(player_id=buzz_message.player_id, clue_id=clue_id)
        player_ids = [p.id for p in session.get_all_players(game_id)]
        await publish_message(
            game_id,
            "PLAYER_BUZZED",
            player_buzz_message,
            [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)])
    else:
        logger.info(f"Player {buzz_message.player_id} buzzed too late.")


@socket_handler.operation("RESPONSE_CORRECT", ResponseCorrectMessage)
async def handle_response_correct(game_id: str, response_correct_message: ResponseCorrectMessage):
    players = session.get_all_players(game_id)

    player = next((p for p in players if p.id == response_correct_message.player_id))
    player.score += int(response_correct_message.amount)
    session.save_player(game_id, player)

    game_board = session.get_game_board(game_id)
    tile = game_board.get_tile(response_correct_message.category_key, str(response_correct_message.amount))
    tile.answered = True

    clue_answered_message = ClueAnswered(
        category_key=response_correct_message.category_key, amount=response_correct_message.amount, answered_correctly=True, player_id=player.id
    )
    player_ids = [p.id for p in players]
    await publish_message(
        game_id,
        "CLUE_ANSWERED",
        clue_answered_message,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )
    await publish_message(
        game_id,
        "TURN_OVER",
        clue_answered_message,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )
    await publish_message(
        game_id,
        "PLAYER_STATE_CHANGED",
        players,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )

    remaining_tiles = game_board.get_remaining_tiles()
    if len(remaining_tiles) == 0:
        await _next_round(players, game_board, game_id)
    session.save_game_board(game_id, game_board)
    await _next_turn(player, game_id)


@socket_handler.operation("RESPONSE_INCORRECT", ResponseIncorrectMessage)
async def handle_response_incorrect(game_id: str, response_incorrect_message: ResponseIncorrectMessage):
    players = session.get_all_players(game_id)
    player = next((p for p in players if p.id == response_incorrect_message.player_id))
    player.score -= int(response_incorrect_message.amount)
    session.save_player(game_id, player)

    game_board = session.get_game_board(game_id)
    tile = game_board.get_tile(response_incorrect_message.category_key, str(response_incorrect_message.amount))
    tile.answered = True
    session.save_game_board(game_id, game_board)

    players_buzzed = session.get_players_buzzed(game_id, tile.id)
    clue_answered_message = ClueAnswered(
        category_key=response_incorrect_message.category_key,
        amount=response_incorrect_message.amount,
        answered_correctly=False,
        player_id=player.id,
        players_buzzed=list(players_buzzed)
    )
    player_ids = [p.id for p in players]
    await publish_message(
        game_id,
        "CLUE_ANSWERED",
        clue_answered_message,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )
    await publish_message(
        game_id,
        "PLAYER_STATE_CHANGED",
        players,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )

    session.reset_buzz_lock(game_id, tile.id)
    if len(players_buzzed) == len(players):
        await publish_message(
            game_id,
            "TURN_OVER",
            clue_answered_message,
            [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
        )

        next_player = get_next_player_when_clue_not_answered_correctly(players)
        await _next_turn(next_player, game_id)


@socket_handler.operation("CLUE_EXPIRED", ClueExpiredMessage)
async def handle_clue_expired(game_id: str, clue_expired_message: ClueExpiredMessage):
    players = session.get_all_players(game_id)
    game_board = session.get_game_board(game_id)
    tile = game_board.get_tile(clue_expired_message.category_key, clue_expired_message.amount)
    tile.answered = True

    clue_answered_message = ClueAnswered(category_key=clue_expired_message.category_key, amount=clue_expired_message.amount, answered_correctly=False)
    player_ids = [p.id for p in players]
    await publish_message(
        game_id,
        "CLUE_ANSWERED",
        clue_answered_message,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )
    await publish_message(
        game_id,
        "TURN_OVER",
        clue_answered_message,
        [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
    )

    remaining_tiles = game_board.get_remaining_tiles()
    if len(remaining_tiles) == 0:
        await _next_round(players, game_board, game_id)
    session.save_game_board(game_id, game_board)

    next_player = get_next_player_when_clue_not_answered_correctly(players)
    await _next_turn(next_player, game_id)


def get_next_player_when_clue_not_answered_correctly(players: list[Player]) -> Player:
    sorted_by_amount = sorted(players, key=lambda p: p.score)
    return sorted_by_amount[0]


async def _next_turn(next_player: Player, game_id: str):
    waiting_for_player_message = WaitingForPlayerMessage(player_name=next_player.name)
    await publish_message(game_id, "WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, [host_channel(game_id), gameboard_channel(game_id)])

    for player in session.get_all_players(game_id):
        if player.id == next_player.id:
            await publish_message(game_id, "PLAYER_TURN_START", PlayerTurnStartMessage(), player_channel(game_id, player.id))
        else:
            await publish_message(game_id, "WAITING_FOR_PLAYER_CHOICE", waiting_for_player_message, player_channel(game_id, player.id))


async def _next_round(players: list[Player], game_board: GameBoard, game_id: str):
    game_board.current_round += 1

    if game_board.current_round >= len(game_board.rounds):
        logger.debug("Game over")
        player_ids = [p.id for p in players]
        await publish_message(
            game_id,
            "GAME_OVER",
            GameOverMessage(players=players),
            [host_channel(game_id), gameboard_channel(game_id), *player_channel(game_id, player_ids)]
        )

    else:
        logger.debug(f"New round: {game_board.current_round}")
        await publish_message(game_id, "NEW_ROUND", NewRoundMessage(), gameboard_channel(game_id))
