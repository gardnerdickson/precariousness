from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class PrecariousnessBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class SocketMessage(BaseModel):
    operation: str
    payload: Union[List[Any], Dict[str, Any]] = {}


class Answer(PrecariousnessBaseModel):
    category: str
    amount: Optional[str]


"""
Game state models
"""


class Question(PrecariousnessBaseModel):
    answer: str
    question: str
    answered: bool = False


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
    player_name: str = Field(alias="playerName")


class StartGameMessage(PrecariousnessBaseModel):
    pass


class SelectQuestionMessage(Answer):
    pass


class DeselectQuestionMessage(Answer):
    pass


class QuestionCorrectMessage(Answer):
    player_name: str = Field(alias="playerName")
    category: str
    amount: int


class QuestionIncorrectMessage(Answer):
    player_name: str = Field(alias="playerName")
    category: str
    amount: int


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


class CategorySelectedMessage(Answer):
    pass


class QuestionSelectedMessage(Answer):
    answer_text: str = Field(alias="answerText")


class QuestionAnswered(Answer):
    pass


class LoadGameBoardMessage(PrecariousnessBaseModel):
    game_board: GameBoardState = Field(alias="gameBoard")


class Player(PrecariousnessBaseModel):
    id: str
    name: str
    score: int
