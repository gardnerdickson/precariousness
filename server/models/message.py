from typing import Optional

from pydantic import Field

from server.models.game_state import Player
from server.models import PrecariousnessBaseModel


"""
HTTP models
"""


class GameId(PrecariousnessBaseModel):
    game_id: str = Field(alias="gameId")


class Clue(PrecariousnessBaseModel):
    category_key: str = Field(alias="categoryKey")
    category: Optional[str]
    amount: Optional[str]


class ClueWithGameId(GameId, Clue):
    pass


"""
Inbound socket communication models
"""


class PlayerInitMessage(PrecariousnessBaseModel):
    player_name: str = Field(alias="playerName")


class PlayerChooseAnswerMessage(PrecariousnessBaseModel):
    category: str
    value: int


class PlayerBuzzMessage(PrecariousnessBaseModel):
    player_id: str = Field(alias="playerId")
    clue_id: str = Field(alias="clueId")


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
    player_id: str = Field(alias="playerId")


class ResponseIncorrectMessage(Clue):
    player_id: str = Field(alias="playerId")


class ClueExpiredMessage(Clue):
    pass


class ErrorMessage(PrecariousnessBaseModel):
    error: str


"""
Outbound socket communication models
"""


class PlayerJoinedMessage(PrecariousnessBaseModel):
    player_id: str = Field(alias="playerId")
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
    answered_correctly: bool = Field(alias="answeredCorrectly")
    player_id: Optional[str] = Field(alias="playerId")
    players_buzzed: Optional[list[str]] = Field(alias="playersBuzzed")


class ClueInfo(PrecariousnessBaseModel):
    clue: str = Field(alias="clue")
    correct_response: str = Field(alias="correctResponse")
    clue_id: str = Field(alias="clueId")


class AllPlayersIn(PrecariousnessBaseModel):
    pass


class NewRoundMessage(PrecariousnessBaseModel):
    pass


class GameOverMessage(PrecariousnessBaseModel):
    players: list[Player]
