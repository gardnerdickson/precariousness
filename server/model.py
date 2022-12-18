from dataclasses import dataclass
from typing import Any, Dict

from pydantic import BaseModel, Field


class PrecariousnessBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class SocketMessage(BaseModel):
    operation: str
    payload: Dict[str, Any] = {}


"""
Inbound socket communication models
"""


class PlayerInitMessage(PrecariousnessBaseModel):
    player_name: str = Field(alias="playerName")


class PlayerChooseAnswerMessage(PrecariousnessBaseModel):
    category: str
    value: int


class PlayerBuzzMessage(PrecariousnessBaseModel):
    pass


class StartGameMessage(PrecariousnessBaseModel):
    pass


class ErrorMessage(PrecariousnessBaseModel):
    error: str


"""
Outbound socket communication models
"""


class PlayerJoinedMessage(PrecariousnessBaseModel):
    player_name: str = Field(alias="playerName")
    player_score: int = Field(alias="playerScore")


class WaitingForPlayerMessage(PrecariousnessBaseModel):
    player_name: str = Field(alias="playerName")


class PlayerTurnStartMessage(PrecariousnessBaseModel):
    pass


"""
Game state models
"""


@dataclass
class Player:
    id: str
    name: str
    score: int
