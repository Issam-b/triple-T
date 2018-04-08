#! /usr/bin/python3

import random
import string
import time
import threading
import helpers as constants
from helpers import setup_logger
from helpers import cmd
from helpers import cmd_buffer
from helpers import game_config
import server_game as sg


# command codenames between sever and client
message_length = int(game_config.get("OTHER", "message_length"))
DEBUG = True if game_config.get("DEBUG", "DEBUG") == "True" else False
logger = setup_logger("settings.conf", "server")


class Player:
    """Player class to keep track of availble players and their status"""
    # count of players connected since the server started

    def __init__(self, conn):
        """called when new player created."""
        sg.GameServer.all_players_count += 1
        self.conn = conn
        self.is_waiting = True
        self.id = sg.GameServer.all_players_count
        logger.info("player with id: " + str(self.id) + " has joined.")
        self.role = ""
        self.opponenet = ""
        self.disconected = False
        self.cmd_buffer = cmd_buffer
        self.dropped = False

    def send(self, command, msg):
        """Send data from server to player"""
        try:
            self.conn.send((command + msg).encode())
            if DEBUG:
                logger.info("sending: " + str(command + msg) +
                            " to: " + str(self.id))
        except Exception:
            logger.error("Send failed to " + str(self.id))
            # assume player connection is lost if an error accured
            self.lost_connection()

    def receive_populate_buffer(self, timeout=5, size=message_length):
        """receive commands and save to buffer untill read by server"""
        try:
            # self.conn.settimeout(timeout)
            msg = self.conn.recv(size).decode()
            if len(msg) > 0:
                if DEBUG:
                    logger.info("received: " + str(msg) +
                                " from: " + str(self.id))
                recv_cmd = ""
                recv_cmd = self.find_cmd_buffer_key(
                    constants.cmd, msg, recv_cmd)

                if recv_cmd == "board":
                    self.cmd_buffer[str(recv_cmd)] = msg[1:]
                elif recv_cmd == "quit":
                    self.cmd_buffer[str(recv_cmd)] = True
                else:
                    self.cmd_buffer[str(recv_cmd)] = msg[1]

                return True
            else:
                return False

        except Exception as e:
            logger.error("Failed while receiving msg from " +
                         str(self.id) + " : " + str(e))
            return False

    def find_cmd_buffer_key(self, cmd, msg, recv_cmd):
        items = cmd.items()
        for key, cmd in items:
            if cmd == msg[0]:
                recv_cmd = key
                break
        return recv_cmd

    def receive_with_wait(self, expected_command, timeout=0):
        """Receive data from player and check the validity of the data."""
        # TODO use locks here
        if timeout == 0:
            while self.cmd_buffer[str(expected_command)] == "" and not self.disconected:
                time.sleep(0.1)
        else:
            time_to_wait = int((round(time.time() + timeout) * 1000))
            while self.cmd_buffer[str(expected_command)] == "" and not self.disconected:
                current_time = int(round(time.time() * 1000))
                if time_to_wait - current_time <= 0:
                    return -1
                time.sleep(0.1)

        cmd_to_return = self.cmd_buffer[str(expected_command)]
        self.cmd_buffer[str(expected_command)] = ""
        return cmd_to_return

    def read_buffer(self, expected_command, clear=True):
        """read the current data from buffer"""
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        if clear:
            self.cmd_buffer[str(expected_command)] = ""
        return cmd_to_return

    def send_game_info(self):
        """send the player his assigned role and matched opponenet."""
        success_state = False
        msg = str(self.id) + str(self.role)
        logger.info("Sending game info to: " + str(self.id))
        self.send(cmd["game_info"], msg)
        try:
            received_confirm_msg = int(self.receive_with_wait("confirm"))
            expected_msg = int(cmd["confirm_states"]["game_info_received"])
            if received_confirm_msg != expected_msg:
                self.lost_connection()
                self.remove_player_from_server("waitlist", "active")
            else:
                self.remove_player_from_server("waitlist")
                success_state = True
        except Exception:
            logger.error("Expected a valid confirm integer")

        return success_state

    def remove_player_from_server(self, waitlist="", active=""):
        if waitlist == "waitlist" and self in sg.GameServer.players_waitlist:
            sg.GameServer.players_waitlist.remove(self)
        if active == "active" and self in sg.GameServer.active_players:
            sg.GameServer.active_players.remove(self)

    def lost_connection(self):
        """Called when connection with player is lost"""
        self.disconected = True
        logger.warning("Player: " + str(self.id) + " has lost connection!")
