import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass


_errors = []

try:
    GAME_FILE = os.environ["GAME_FILE"]
except KeyError as exc:
    _errors.append(str(exc))

try:
    REDIS_HOST = os.environ["REDIS_HOST"]
except KeyError as exc:
    _errors.append(str(exc))

try:
    REDIS_PORT = os.environ["REDIS_PORT"]
except KeyError as exc:
    _errors.append(str(exc))


if _errors:
    raise KeyError(f"Required environment variables missing: {', '.join(_errors)}")
