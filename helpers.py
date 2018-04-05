import logging
import logging.config
from configparser import ConfigParser

game_config = ConfigParser()
game_config.read('settings.conf')


def setup_logger(config_file, name):
    logging.config.fileConfig(config_file)
    logger = logging.getLogger(name)

    return logger
