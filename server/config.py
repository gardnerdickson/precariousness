import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass


def get_redis_config() -> tuple[str, str, Optional[str]]:
    if "AWS_DEFAULT_REGION" in os.environ:
        logger.info("In AWS. Getting Redis config from Parameter Store")
        ssm = boto3.client("ssm")
        try:
            redis_parameters = ssm.get_parameters_by_path(Path="/precariousness/prod/redis", WithDecryption=True)
            indexed_parameters = {p["Name"]: p["Value"] for p in redis_parameters["Parameters"]}
            host = indexed_parameters["/precariousness/prod/redis/host"]
            port = indexed_parameters["/precariousness/prod/redis/port"]
            password = indexed_parameters["/precariousness/prod/redis/password"]
            return host, port, password
        except ClientError as e:
            logger.error(f"Failed to get Redis parameters: {e}")
            raise e
    else:
        logger.info("Not in AWS. Looking for Redis config in environment variables")
        _errors = []

        try:
            host = os.environ["REDIS_HOST"]
        except KeyError as exc:
            _errors.append(str(exc))

        try:
            port = os.environ["REDIS_PORT"]
        except KeyError as exc:
            _errors.append(str(exc))

        if _errors:
            raise KeyError(f"Required environment variables missing: {', '.join(_errors)}")

        return host, port, None
