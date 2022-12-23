class InvalidPlayerId(Exception):
    def __init__(self, player_id):
        self.player_id = player_id


class InvalidOperation(Exception):
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
