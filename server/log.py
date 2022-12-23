import logging.config


def configure_logging():
    ini_file = "server/logging.conf"
    logging.config.fileConfig(ini_file, disable_existing_loggers=False)
