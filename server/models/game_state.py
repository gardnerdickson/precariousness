from typing import Dict, List

from pydantic import Field

from server.models import PrecariousnessBaseModel


class Tile(PrecariousnessBaseModel):
    clue: str
    correct_response: str
    answered: bool = False


class Category(PrecariousnessBaseModel):
    name: str
    tiles: Dict[str, Tile]


class GameBoardState(PrecariousnessBaseModel):
    rounds: List[List[Category]] = Field(default_factory=list)
    current_round: int = Field(default=0, alias="currentRound")


class Player(PrecariousnessBaseModel):
    id: str
    name: str
    score: int
