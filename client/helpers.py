import logging
import logging.config
from configparser import ConfigParser

cmd = {
    'move': 'm',
    'quit': 'q',
    'echo': 'e',
    'confirm': 'c',
    'timeout': 't',
    'confirm_states': {
        'game_info_received': '1',
        'id_received': '2'
    },
    'state': 's',
    'state_types': {
        'lose': 'l',
        'win': 'w',
        'draw': 'd',
        'your_turn': 'u',
        'other_turn': 'o',
        'other_disconnected': 'z'
    },
    'board': 'b',
    'game_info': 'g'
}

cmd_buffer = {
    'move': '',
            'board': '',
            'quit': '',
            'echo': '',
            'confirm': '',
            'state': '',
            'timeout': '',
            'game_info': ''
}

game_config = ConfigParser()
game_config.read("settings.conf")


def setup_logger(config_file, name):
    logging.config.fileConfig(config_file)
    logger = logging.getLogger(name)

    return logger
