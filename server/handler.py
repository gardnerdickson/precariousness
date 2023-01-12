import json
import logging

from typing import Type, Union, List

from starlette.websockets import WebSocket

from server.exceptions import InvalidOperation
from server.models import PrecariousnessBaseModel, SocketMessage


logger = logging.getLogger(__name__)


class SocketHandler:
    def __init__(self):
        self.operation_handlers = {}
        self.error_handlers = {}

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
        try:
            data = await websocket.receive_json()
            logger.debug(f"Processing message: {json.dumps(data)}")
            message = SocketMessage.parse_obj(data)
            if message.operation not in self.operation_handlers:
                raise InvalidOperation(message.operation)
            logger.info(f"Routing operation: {message.operation}")
            func, model_type = self.operation_handlers[message.operation]
            payload = model_type.parse_obj(message.payload)
            return await func(payload, **kwargs)
        except Exception as e:
            await self.handle_error(websocket, e)

    async def handle_error(self, websocket: WebSocket, exc: Exception):
        bases = type(exc).mro()
        for base in bases:
            if base in self.error_handlers:
                await self.error_handlers[base](websocket, exc)
                return
        logger.warning(f"No handler registered for exception: {type(exc)}")
        raise exc

    @staticmethod
    async def send_message(operation: str, message: Union[PrecariousnessBaseModel, List[PrecariousnessBaseModel]], sockets: Union[WebSocket, List[WebSocket]]):
        if isinstance(message, list):
            message = [m.dict(by_alias=True) for m in message]
            data = SocketMessage(operation=operation, payload=message).dict(by_alias=True)
        else:
            data = SocketMessage(operation=operation, payload=message.dict(by_alias=True)).dict(by_alias=True)
        if isinstance(sockets, WebSocket):
            sockets = [sockets]
        for socket in sockets:
            await socket.send_json(data)
