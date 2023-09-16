import asyncio
import json
import logging
from typing import Type, Callable, Awaitable

import redis.asyncio as redis
from fastapi import WebSocket
from starlette.websockets import WebSocketState

import server.config as config
from server.exceptions import InvalidOperation
from server.models import PrecariousnessBaseModel, SocketMessage

logger = logging.getLogger(__name__)


host, port, password = config.get_redis_config()
user_part = f":{password}@" if password is not None else ""
_redis_client = redis.StrictRedis.from_url(f"redis://{user_part}{host}:{port}")
_redis_pubsub = _redis_client.pubsub()


class SocketHandler:
    def __init__(self):
        self.operation_handlers: dict[str, tuple[Callable, Type[PrecariousnessBaseModel]]] = {}
        self.error_handlers: dict[Type, Callable[[WebSocket, Exception], Awaitable[str | dict]]] = {}

    def operation(self, operation_name: str, model_type: Type[PrecariousnessBaseModel]):
        if operation_name in self.operation_handlers:
            raise KeyError(f"Operation name '{operation_name}' already in use")

        def decorator(func):
            self.operation_handlers[operation_name] = (func, model_type)

        return decorator

    def error(self, exception_type: Type[Exception]):
        if exception_type in self.error_handlers:
            raise KeyError(f"Exception type '{exception_type}' already registered")

        def decorator(func):
            self.error_handlers[exception_type] = func

        return decorator

    async def handle_operation(self, websocket: WebSocket, **kwargs):
        while websocket.application_state == WebSocketState.CONNECTED:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Processing message: {json.dumps(data)}")
                message = SocketMessage.parse_obj(data)
                if message.operation not in self.operation_handlers:
                    raise InvalidOperation(message.operation)
                logger.info(f"Routing operation: {message.operation}")
                func, model_type = self.operation_handlers[message.operation]
                payload = model_type.parse_obj(message.payload)
                await func(message.game_id, payload, **kwargs)
            except Exception as e:
                await self.handle_error(websocket, e)

    async def handle_error(self, websocket: WebSocket, exc: Exception):
        bases = type(exc).mro()
        for base in bases:
            if base in self.error_handlers:
                error_message = await self.error_handlers[base](websocket, exc)
                if error_message and websocket.application_state == WebSocketState.CONNECTED:
                    await websocket.send_json({"error": error_message})
                return
        logger.warning(f"No handler registered for exception: {type(exc)}")
        raise exc


def player_channel(game_id: str, player_ids: str | list[str]) -> str | list[str]:
    if not isinstance(player_ids, list):
        player_ids = [player_ids]

    channels = [f"{game_id}:channel:player:{p_id}" for p_id in player_ids]
    return channels[0] if len(channels) == 1 else channels


def host_channel(game_id: str) -> str:
    return f"{game_id}:channel:host"


def gameboard_channel(game_id: str) -> str:
    return f"{game_id}:channel:gameboard"


_sockets: dict[str, WebSocket] = {}
_routing_task = None


async def _route_messages():
    while True:
        channel_data = await _redis_pubsub.get_message(ignore_subscribe_messages=True)
        if channel_data is not None:
            channel = channel_data["channel"].decode()
            await _sockets[channel].send_text(channel_data["data"])


async def register_socket_route(channel: str, websocket: WebSocket):
    await _redis_pubsub.subscribe(channel)
    _sockets[channel] = websocket
    logger.info(f"Registered websocket for channel \"{channel}\"")

    global _routing_task
    if not _routing_task:
        _routing_task = asyncio.create_task(_route_messages())


async def unregister_socket_route(channel: str):
    await _redis_pubsub.unsubscribe(channel)
    del _sockets[channel]


async def publish_message(game_id: str, operation: str, message: PrecariousnessBaseModel | list[PrecariousnessBaseModel], channels: str | list[str]):
    if isinstance(message, list):
        message = [m.dict(by_alias=True) for m in message]
        data = SocketMessage(operation=operation, payload=message, game_id=game_id).dict(by_alias=True)
    else:
        data = SocketMessage(operation=operation, payload=message.dict(by_alias=True), game_id=game_id).dict(by_alias=True)
    if not isinstance(channels, list):
        channels = [channels]

    for channel in channels:
        await _redis_client.publish(channel, json.dumps(data))
