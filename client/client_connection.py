#! /usr/bin/python3

import ssl
import socket
import time
from helpers import setup_logger
import client_game as cg
import helpers as constants
from helpers import cmd
from helpers import game_config

logger = setup_logger("settings.conf", "client")
CERT = game_config.get("SSL", "CERT")
DEBUG = True if game_config.get("DEBUG", "DEBUG") == "True" else False
message_length = int(game_config.get("OTHER", "message_length"))
TIMEOUT = int(game_config.get("OTHER", "TIMEOUT"))


class ClientConnection():
    """class to handle connection to server, receive and send"""
    # buffer for received data
    cmd_buffer = constants.cmd_buffer

    def __init__(self):
        """ini the class objects"""
        # 1st parameter: IPv4 networking
        # 2nd parameter: socket type, SOCK_STREAM = TCP
        # self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def client_connect(self):
        """connect to server function"""
        fail_counter = 0
        while True:
            if fail_counter == 0:
                address = game_config.get("connection", "address")
                port = game_config.get("connection", "port")
            if fail_counter == 1:
                address = game_config.get("connection", "address2")
                port = game_config.get("connection", "port2")

            logger.info("Trying to connect to server " +
                        str(fail_counter + 1) + " on " + str(address) + ":" + str(port))
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket = ssl.wrap_socket(
                    self.socket, cert_reqs=ssl.CERT_REQUIRED, ca_certs=CERT)
                self.client_socket.connect((address, int(port)))
                logger.info("Connected to Server")
                break
            except Exception:
                logger.error("Error connecting to " +
                             str(address) + ":" + str(port))
            finally:
                time.sleep(1)
            fail_counter += 1
            if fail_counter > 1:
                logger.info("All servers are down")
                exit(-1)

    def receive_populate_buffer(self, size=message_length):
        """receive commands and save to buffer untill read by server"""
        try:
            # self.client_socket.settimeout(TIMEOUT)
            msg = self.client_socket.recv(size).decode()
            if len(msg) > 0:
                if DEBUG:
                    logger.info("received: " + str(msg))
                recv_cmd = ""
                recv_cmd = self.find_cmd_buffer_key(
                    constants.cmd, msg, recv_cmd)

                if recv_cmd == "board" or recv_cmd == "game_info":
                    self.cmd_buffer[str(recv_cmd)] = msg[1:]
                elif recv_cmd == "timeout":
                    self.cmd_buffer[str(recv_cmd)] = True
                else:
                    self.cmd_buffer[str(recv_cmd)] = msg[1]
            else:
                self.connection_lost()

        except Exception as es:
            logger.error("Got exception while receiving msg: " + str(es))
            self.connection_lost()

    def find_cmd_buffer_key(self, cmd, msg, recv_cmd):
        items = cmd.items()
        for key, cmd in items:
            if cmd == msg[0]:
                recv_cmd = key
                break
        return recv_cmd

    def client_receive_with_wait(self, expected_command, clear=True):
        """Receive data from player and check the validity of the data."""
        while self.cmd_buffer[str(expected_command)] == "":
            if cg.Game.game_ended:
                break
            time.sleep(0.1)
        return self.read_buffer(expected_command, clear)

    def read_buffer(self, expected_command, clear=True):
        """read the current data from buffer"""
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        if clear:
            self.cmd_buffer[str(expected_command)] = ""
        return cmd_to_return

    def client_send(self, cmd, msg):
        """Send data from server to player"""
        try:
            if DEBUG:
                logger.info("Sending: " + str(cmd + msg))
            self.client_socket.send((cmd + msg).encode())
        except Exception as e:
            logger.error("Send exception, " + str(e))
            # assume player is lost if an error accured
            self.connection_lost()

    def connection_lost(self):
        """called when connection is lost"""
        logger.error("Connection lost!")
        cg.Game.game_ended = True
        exit(-1)

    def close(self):
        """close the connection"""
        # self.client_socket.shutdown(socket.SHUT_RDWR)
        logger.info("Closing socket")
        self.client_socket.close()
