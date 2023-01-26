from typing import Optional, List

from pydantic import Field

from server.models.game_state import Player
from server.models import PrecariousnessBaseModel


class Clue(PrecariousnessBaseModel):
    category: str
    amount: Optional[str]


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


class SelectCategoryMessage(Clue):
    pass


class DeselectCategoryMessage(Clue):
    pass


class SelectClueMessage(Clue):
    pass


class ClueRevealedMessage(Clue):
    pass


class ResponseCorrectMessage(Clue):
    player_name: str = Field(alias="playerName")
    category: str
    amount: int


class ResponseIncorrectMessage(Clue):
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


class CategorySelectedMessage(Clue):
    pass


class ClueSelectedMessage(Clue):
    clue_text: str = Field(alias="clueText")


class ClueAnswered(Clue):
    pass


class ClueInfo(PrecariousnessBaseModel):
    clue: str = Field(alias="clue")
    correct_response: str = Field(alias="correctResponse")


class AllPlayersIn(PrecariousnessBaseModel):
    pass


class NewRoundMessage(PrecariousnessBaseModel):
    pass


class GameOverMessage(PrecariousnessBaseModel):
    players: List[Player]
