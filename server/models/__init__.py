from typing import Dict, Any, List, Union, Optional

from pydantic import BaseModel, Field


class PrecariousnessBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class SocketMessage(BaseModel):
    operation: str
    payload: Union[List[Any], Dict[str, Any]] = {}
    game_id: Optional[str] = Field(alias="gameId")
