#! /usr/bin/python3

import time
import threading
import _thread
from helpers import setup_logger
from constants import cmd
import signal
from helpers import game_config
import keyboard

logger = setup_logger('settings.conf', 'client')
TIMEOUT = int(game_config.get('OTHER', 'TIMEOUT'))


class Game():
    """handle gameplay logic"""

    game_ended = False
    timed_out = False

    def __init__(self, connection):
        """init function for game, connect to server and start receive threads"""
        self.game_started = False
        self.connection = connection
        self.connection.client_connect()
        self.id = ''
        self.role = ''

        threading.Thread(
            target=self.id_role_thread, args=(), daemon=True).start()
        threading.Thread(
            target=self.check_states, args=(), daemon=True).start()
        threading.Thread(
            target=self.fetch_data, args=(), daemon=True).start()

    def fetch_data(self):
        """fetch data from server periodically"""
        while True:
            self.connection.receive_populate_buffer()
            if Game.game_ended:
                break

    def id_role_thread(self):
        """get intial id and role and confirm them"""
        while True:
            try:
                self.reply_echo()
                if not self.game_started:
                    self.confirm_role()
                else:
                    break

            except Exception as e:
                logger.error(
                    "Exception on id_role_thread states thread, " + str(e))

            time.sleep(0.2)

    def check_states(self):
        """check conneciton to server periodically"""
        logger.info('Running connection check thread')
        while True:
            try:
                state = self.connection.read_buffer('state', False)
                if state == cmd['state_types']['other_disconnected']:
                    logger.info('Opponent disconnected, You won!')
                    Game.game_ended = True
                    break
                isTimedOut = self.connection.read_buffer('timeout')
                if isTimedOut is True:
                    logger.info('Turn timedout, next turn')
                    Game.timed_out = True

            except Exception as e:
                logger.error("Exception on check states thread, " + str(e))

            time.sleep(0.2)

    def confirm_role(self):
        """receive the role and send confirmation to the server"""
        id_role = self.connection.read_buffer('game_info')
        if id_role != '':
            self.id = id_role[0]
            self.role = id_role[1:]
            print('My role is: ' + str(self.role) +
                  ' and id is: ' + str(self.id))
            logger.info('Confirming player role is: ' + str(id_role))
            self.connection.client_send(
                cmd['confirm'], cmd['confirm_states']['game_info_received'])
            self.game_started = True

    def reply_echo(self):
        """reply to the server that the conneciton is still active"""
        echo_value = self.connection.read_buffer('echo')
        if echo_value != '':
            self.connection.client_send(cmd['echo'], echo_value)

    def convert_empty_board_position(self, board):
        """Convert board into readable board with X and O"""
        new_board = list("123456789")
        for i in range(0, 9):
            if board[i] != ' ':
                new_board[i] = board[i]

        return "".join(new_board)

    def format_board(self, board):
        """return the board values formatted to print"""
        if len(board) != 9:
            logger.error("Error: there should be 9 symbols")
            return ""

        # return the grid board
        row1 = "|" + board[0] + "|" + board[1] + "|" + board[2] + "|\n"
        row2 = "|" + board[3] + "|" + board[4] + "|" + board[5] + "|\n"
        row3 = "|" + board[6] + "|" + board[7] + "|" + board[8] + "|\n"
        return row1 + row2 + row3

    def start(self):
        """run the game logic"""

        while True:
            board_content = self.connection.client_receive('board')
            state = self.connection.client_receive('state')

            if Game.game_ended:
                break

            # If it's this player's turn to move
            if state == cmd['state_types']['your_turn']:
                # Print out the current board with " " converted to the position number
                print('Current board:\n' +
                      self.format_board(self.convert_empty_board_position(board_content)))
                Game.timed_out = False
                while True:
                    position = 0
                    try:
                        if Game.timed_out:
                            # logger.info("Timeout from server, break input")
                            break
                        signal.signal(signal.SIGALRM, self.interrupted)
                        signal.alarm(TIMEOUT)
                        choice = self.input('You have ' + str(TIMEOUT) +
                                            ' seconds, please enter the postion (1~9): ')
                        signal.alarm(0)

                        if choice == 'q':
                            self.connection.client_send(
                                cmd['quit'], '')
                            logger.info('Exiting game')
                            exit()
                        else:
                            position = int(choice)
                    except Exception as e:
                        if Game.game_ended:
                            break
                        logger.error(
                            'Expecting an integer number, ' + str(e))
                        pass
                    if position >= 1 and position <= 9:
                        if board_content[position - 1] != " ":
                            logger.info(
                                'That postion is already taken. Please choose another')
                        else:
                            self.connection.client_send(
                                cmd['move'], str(position))
                            break
            else:
                print('Current board:\n' + self.format_board(board_content))

                if state == cmd['state_types']['other_turn']:
                    logger.info("Waiting for the other player to make a move")

                elif state == cmd['state_types']['draw']:
                    logger.info("It's a draw.")
                    break

                elif state == cmd['state_types']['win']:
                    logger.info("You WIN!")
                    break

                elif state == cmd['state_types']['lose']:
                    logger.info("You lose.")
                    break

    def interrupted(self, signum, frame):
        """called when input times out"""
        print('interrupted!')
        keyboard.press_and_release('enter')

    def input(self, message):
        try:
            line = input(message)
            return line
        except:
            return
