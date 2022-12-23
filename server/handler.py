from typing import Type

from starlette.websockets import WebSocket

from server.exceptions import InvalidOperation
from server.model import PrecariousnessBaseModel, SocketMessage


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
            message = SocketMessage.parse_obj(data)
            if message.operation not in self.operation_handlers:
                raise InvalidOperation(message.operation)
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
        raise exc

    @staticmethod
    async def send_message(operation: str, message: PrecariousnessBaseModel, socket: WebSocket):
        message = SocketMessage(operation=operation, payload=message.dict(by_alias=True))
        await socket.send_json(message.dict(by_alias=True))
