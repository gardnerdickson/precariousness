from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PrecariousnessBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class SocketMessage(BaseModel):
    operation: str
    payload: Dict[str, Any] = {}


class Tile(PrecariousnessBaseModel):
    category: str
    amount: Optional[str]


"""
Game state models
"""


class Question(PrecariousnessBaseModel):
    answer: str
    question: str
    used: bool = True


class Category(PrecariousnessBaseModel):
    name: str
    questions: Dict[str, Question]


class Round(PrecariousnessBaseModel):
    categories: List[Category]


class GameBoardState(PrecariousnessBaseModel):
    rounds: List[Round]
    current_round: int = Field(default=0, alias="currentRound")


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


class SelectQuestionMessage(Tile):
    pass


class DeselectQuestionMessage(Tile):
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


class CategorySelectedMessage(Tile):
    pass


class QuestionSelectedMessage(Tile):
    answer_text: str = Field(alias="answerText")


class LoadGameBoardMessage(PrecariousnessBaseModel):
    game_board: GameBoardState = Field(alias="gameBoard")


@dataclass
class Player:
    id: str
    name: str
    score: int
