#! /usr/bin/python3

import socket
import ssl
from helpers import setup_logger
from helpers import game_config

logger = setup_logger('settings.conf', 'client')
KEY = game_config.get('SSL', 'KEY')
CERT = game_config.get('SSL', 'CERT')


class Server:
    """Server class to handle connection related calls."""

    def __init__(self):
        """Initializes the server object with a server socket."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def bind_server(self, host, port):
        """bind and listen to the the given port."""
        while True:
            try:
                self.server_socket.bind((host, int(port)))
                logger.info('Bind successful to port ' + str(port))
                self.server_socket.listen(5)
                self.socket_ssl = ssl.wrap_socket(
                    self.server_socket, keyfile=KEY, certfile=CERT, server_side=True)
                logger.info('Listening on port ' + str(port))
                break

            except socket.error as e:
                logger.error("Got an error while connecting, " + str(e))
                exit(-1)

    def close(self):
        logger.info('Closing socket')
        self.server_socket.close()
