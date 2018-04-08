#! /usr/bin/python3

from configparser import ConfigParser
from helpers import cmd
from helpers import setup_logger
from helpers import game_config
from server_game import GameServer
import signal

logger = setup_logger("settings.conf", "server")
port = game_config.get("connection", "port")
server = GameServer("", int(port))


def handle_keyboard_interrupts(signum, frame):
    server.close()
    exit(-1)


def main():
    signal.signal(signal.SIGINT, handle_keyboard_interrupts)

    try:
        server.start()
        server.close()
        logger.info("Exiting")

    except Exception as e:
        logger.error("Unexpected exit of game" + str(e))
        server.close()
        exit(-1)


if __name__ == __name__:
    main()
