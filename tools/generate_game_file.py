import argparse
import csv
import json
import os
import random
from dataclasses import dataclass, asdict

from typing import Dict, List


@dataclass
class Tile:
    clue: str
    correct_response: str


@dataclass
class Category:
    name: str
    tiles: Dict[str, Tile]


_ROUND_BLACKLIST = {"Final Jeopardy!", "Tiebreaker"}
_CATEGORIES_PER_ROUND = 5


def get_all_no_media_categories(reader):
    categories_by_round = [{}, {}]
    media_categories = set()

    round_to_index = {
        "Jeopardy!": 0,
        "Double Jeopardy!": 1
    }

    def format_amount(amount: str):
        return amount.replace("$", "").replace(",", "")

    for row in reader:
        row_round = row["Round"]
        if row_round in _ROUND_BLACKLIST:
            continue
        round_index = round_to_index[row_round]
        key = row["Show Number"] + "#" + row["Category"]
        if "href" in row["Question"]:
            media_categories.add(key)
            continue
        if key not in categories_by_round[round_index]:
            categories_by_round[round_index][key] = Category(
                name=row["Category"],
                tiles={format_amount(row["Value"]): Tile(clue=row["Question"], correct_response=row["Answer"])}
            )
        else:
            categories_by_round[round_index][key].tiles[format_amount(row["Value"])] = Tile(clue=row["Question"], correct_response=row["Answer"])

    categories_by_round[0] = {k: v for k, v in categories_by_round[0].items() if len(v.tiles) == 5}
    categories_by_round[1] = {k: v for k, v in categories_by_round[1].items() if len(v.tiles) == 5}

    no_media_categories = [{}, {}]
    no_media_categories[0] = {k: v for k, v in categories_by_round[0].items() if k not in media_categories}
    no_media_categories[1] = {k: v for k, v in categories_by_round[1].items() if k not in media_categories}
    return no_media_categories


def generate_game(keys_by_round: List[List[str]], categories_by_round: List[Dict[str, Category]]) -> Dict:
    rounds = [[], []]
    for _ in range(_CATEGORIES_PER_ROUND):
        for rnd in range(2):
            category = categories_by_round[rnd][keys_by_round[rnd].pop()]
            sorted_tiles = sorted(category.tiles.items(), key=lambda item: int(item[0]))
            amount = 0
            category.tiles.clear()
            for _, clue in sorted_tiles:
                amount = amount + (200 * (rnd + 1))
                category.tiles[str(amount)] = clue
            rounds[rnd].append(asdict(category))

    return {"rounds": [rounds[0], rounds[1]]}


def generate(csv_path: str, output_path: str):

    with open(csv_path) as fh:
        reader = csv.DictReader(fh)
        round_0_categories, round_1_categories = get_all_no_media_categories(reader)

    round_0_category_keys = list(round_0_categories.keys())
    random.shuffle(round_0_category_keys)
    round_1_category_keys = list(round_1_categories.keys())
    random.shuffle(round_1_category_keys)

    keys_by_round = [round_0_category_keys, round_1_category_keys]
    categories_by_round = [round_0_categories, round_1_categories]

    prefix_counter = 0
    debug_limit = 3
    while len(keys_by_round[0]) > 9 and len(keys_by_round[1]) > 9:
        game = generate_game(keys_by_round, categories_by_round)
        filename = f"{prefix_counter}.json"
        with open(os.path.join(output_path, filename), mode="w") as game_fh:
            json.dump(game, game_fh)
        prefix_counter += 1

        debug_limit -= 1
        if debug_limit == 0:
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Generate Precariousness game file from CSV")
    parser.add_argument("--csv", action="store", dest="csv_path", help="Path to csv file")
    parser.add_argument("--output", action="store", dest="output_path", help="Path to output directory")
    args = parser.parse_args()
    generate(args.csv_path, args.output_path)
