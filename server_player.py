#! /usr/bin/python3

import random
import string
import time
from helpers import setup_logger
import server_game as sg
import constants
from constants import cmd
from constants import cmd_buffer
from helpers import game_config

# command codenames between sever and client
message_length = int(game_config.get('OTHER', 'message_length'))
DEBUG = True if game_config.get('DEBUG', 'DEBUG') == 'True' else False
logger = setup_logger('settings.conf', 'server')


class Player:
    """Player class to keep track of availble players and their status"""
    # count of players connected since the server started

    def __init__(self, conn):
        """called when new player created."""
        # update players count
        sg.GameServer.players_count_history += 1
        self.conn = conn
        self.is_waiting = True
        # self.id = self.id_generator()
        self.id = sg.GameServer.players_count_history
        logger.info('player with id: ' + str(self.id) + ' has joined.')
        self.role = ''
        self.opponenet = ''
        self.disconected = False
        self.cmd_buffer = cmd_buffer

    def send(self, command, msg):
        """Send data from server to player"""
        try:
            self.conn.send((command + msg).encode())
            if DEBUG:
                logger.info('sending: ' + str(command + msg) +
                            ' to: ' + str(self.id))
        except Exception as e:
            # assume player connection is lost if an error accured
            logger.error("Send exception: " + str(e))
            self.lost_connection()

    def receive_populate_buffer(self, timeout=5, size=message_length):
        """receive commands and save to buffer untill read by server"""
        try:
            # if timeout > 0:
            # self.conn.settimeout(timeout)
            msg = self.conn.recv(size).decode()
            if len(msg) > 0:
                if DEBUG:
                    logger.info('received: ' + str(msg) +
                                ' from: ' + str(self.id))
                recv_cmd = ''

                cmd = constants.cmd
                items = cmd.items()
                for key, cmd in items:
                    if cmd == msg[0]:
                        recv_cmd = key
                        break

                if recv_cmd == 'board':
                    self.cmd_buffer[str(recv_cmd)] = msg[1:]
                elif recv_cmd == 'quit':
                    self.cmd_buffer[str(recv_cmd)] = True
                else:
                    self.cmd_buffer[str(recv_cmd)] = msg[1]

        except Exception as es:
            logger.error('Got exception while receiving msg: ' + str(es))

    def receive(self, expected_command, timeout=0):
        """Receive data from player and check the validity of the data."""
        # TODO use locks here
        # fetch data
        if timeout == 0:
            while self.cmd_buffer[str(expected_command)] == '' and not self.disconected:
                time.sleep(0.1)
        else:
            time_to_wait = int((round(time.time() + timeout) * 1000))
            while self.cmd_buffer[str(expected_command)] == '' and not self.disconected:
                current_time = int(round(time.time() * 1000))
                if time_to_wait - current_time <= 0:
                    return -1
                # self.receive_populate_buffer()
                time.sleep(0.1)

        # read buffer and save value needed
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        self.cmd_buffer[str(expected_command)] = ''

        return cmd_to_return

    def read_buffer(self, expected_command, clear=True):
        """read the current data from buffer"""
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        if clear:
            self.cmd_buffer[str(expected_command)] = ''

        return cmd_to_return

    def send_game_info(self):
        """send the player his assigned role and matched opponenet."""
        # send game info to player
        success_state = False
        msg = str(self.id) + str(self.role)
        logger.info('Sending game info to: ' + str(self.id))
        # tries to send for two times if having an error at first
        self.send(cmd['game_info'], msg)
        try:
            if int(self.receive('confirm')) != int(cmd['confirm_states']['game_info_received']):
                self.lost_connection()
                # on no confirmation remove player server lists since it's disconnected
                if self in sg.GameServer.players_waitlist:
                    sg.GameServer.players_waitlist.remove(self)
                if self in sg.GameServer.active_players:
                    sg.GameServer.active_players.remove(self)
            else:
                # sent and receive successful
                if self in sg.GameServer.players_waitlist:
                    sg.GameServer.players_waitlist.remove(self)
                success_state = True

        except Exception as e:
            logger.error(
                'Expected a valid integer, exception message: ' + str(e))

        return success_state

    def lost_connection(self):
        """Called when connection with player is lost"""
        self.disconected = True
        logger.warning('Player: ' + str(self.id) + ' has lost connection!')

    def id_generator(self, size=4, chars=string.ascii_lowercase + string.digits):
        """Generate random id strings for the players, just for a unique id"""
        return ''.join(random.choice(chars) for _ in range(size))
