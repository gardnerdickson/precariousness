from typing import Dict, Any, List, Union

from pydantic import BaseModel


class PrecariousnessBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class SocketMessage(BaseModel):
    operation: str
    payload: Union[List[Any], Dict[str, Any]] = {}
