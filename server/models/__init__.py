from typing import Any, Optional

from pydantic import BaseModel, Field


class PrecariousnessBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class SocketMessage(PrecariousnessBaseModel):
    operation: str
    payload: list[Any] | dict[str, Any] = {}
    game_id: Optional[str] = Field(alias="gameId")
