import re

from typing import Dict, List

from pydantic import Field, validator, root_validator

from server.models import PrecariousnessBaseModel

_NON_ALPHANUMERIC = r'[^A-Za-z0-9\_]'


class Tile(PrecariousnessBaseModel):
    clue: str
    correct_response: str
    answered: bool = False


class Category(PrecariousnessBaseModel):
    name: str
    tiles: Dict[str, Tile]
    key: str

    @root_validator(pre=True)
    def initialize_key(cls, values: dict) -> dict:
        values["key"] = re.sub(_NON_ALPHANUMERIC, "", values["name"].replace(" ", "_"))
        return values


class GameBoardState(PrecariousnessBaseModel):
    rounds: List[List[Category]] = Field(default_factory=list)
    current_round: int = Field(default=0, alias="currentRound")

    def get_tile(self, category_key: str, amount: str) -> Tile:
        categories = self.rounds[self.current_round]
        category = next((c for c in categories if c.key == category_key), None)
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
