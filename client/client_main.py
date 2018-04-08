#! /usr/bin/python3

from client_game import Game
from client_connection import ClientConnection
from helpers import setup_logger
import signal

logger = setup_logger("settings.conf", "client")
# create game object to server, connect automatically
connection = ClientConnection()


def handle_keyboard_interrupts(signum, frame):
    connection.close()
    logger.info("Exiting")
    exit(-1)


def main():
    """Main function of the client"""
    signal.signal(signal.SIGINT, handle_keyboard_interrupts)
    Game(connection).start()
    connection.close()
    logger.info("Exiting")


if __name__ == "__main__":
    main()
