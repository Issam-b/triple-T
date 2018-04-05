#! /usr/bin/python3

from client_game import Game
from client_connection import ClientConnection
from helpers import setup_logger

logger = setup_logger('settings.conf', 'client')


def main():
    """Main function of the client"""

    # create game object to server, connect automatically
    connection = ClientConnection()

    # start game
    game = Game(connection)
    game.start()

    # close the connection
    connection.close()


if __name__ == '__main__':
    main()
