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

    def get_tile(self, category: str, amount: str) -> Tile:
        categories = self.rounds[self.current_round]
        category = next((c for c in categories if c.name == category), None)
        if not category:
            raise KeyError(f"Category does not exist: {category}")
        return category.tiles[amount]

    def get_remaining_tiles(self) -> List[Tile]:
        remaining_answers = []
        categories = self.rounds[self.current_round]
        for category in categories:
            remaining_answers.extend([a for a in category.tiles.values() if not a.answered])
        return remaining_answers


class Player(PrecariousnessBaseModel):
    id: str
    name: str
    score: int
