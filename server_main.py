#! /usr/bin/python3

from configparser import ConfigParser
from constants import cmd
from helpers import setup_logger
from helpers import game_config
from server_game import GameServer

logger = setup_logger('settings.conf', 'server')


def main():
    port = game_config.get('connection', 'port')
    try:
        server = GameServer('', int(port)).start()
        server.close()
        logger.info('Exiting')

    except Exception as e:
        logger.error("Unexpected exit of game" + str(e))
        server.close()
        exit(-1)


if __name__ == __name__:
    main()
