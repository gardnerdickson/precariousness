from dataclasses import dataclass
from typing import Any, Dict

from pydantic import BaseModel, Field

"""
Socket communication models
"""


class SocketMessage(BaseModel):
    operation: str
    payload: Dict[str, Any] = {}


class PlayerInitMessage(BaseModel):
    player_name: str = Field(alias="playerName")


class PlayerChooseAnswerMessage(BaseModel):
    category: str
    value: int


class PlayerBuzzMessage(BaseModel):
    pass


class ErrorMessage(BaseModel):
    error: str


"""
Game state models
"""


@dataclass
class Player:
    id: str
    name: str
    score: int
