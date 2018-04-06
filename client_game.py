#! /usr/bin/python3

import time
import threading
import _thread
from helpers import setup_logger
from constants import cmd
import signal
from helpers import game_config
from pynput.keyboard import Key, Controller

logger = setup_logger('settings.conf', 'client')
TIMEOUT = int(game_config.get('OTHER', 'TIMEOUT'))
connection_threads_sleep = float(
    game_config.get('OTHER', 'connection_threads_sleep'))
keyboard = Controller()


class Game():
    """handle gameplay logic"""

    game_ended = False
    timed_out = False

    def __init__(self, connection):
        """init function for game, connect to server and start receive threads"""
        self.connection = connection
        self.game_started = False
        self.connection.client_connect()
        self.id = ''
        self.role = ''
        self.start_connection_daemon_threads()

    def start_connection_daemon_threads(self):
        threading.Thread(
            target=self.id_role_thread, args=(), daemon=True).start()
        threading.Thread(
            target=self.check_game_states_thread, args=(), daemon=True).start()
        threading.Thread(
            target=self.fetch_data_thread, args=(), daemon=True).start()

    def fetch_data_thread(self):
        """fetch data from server periodically"""
        while True:
            self.connection.receive_populate_buffer()
            if Game.game_ended:
                break

    def id_role_thread(self):
        """get intial id and role and confirm them"""
        while True:
            try:
                if not self.game_started:
                    self.confirm_role()
                else:
                    break
            except Exception as e:
                logger.error(
                    "Exception on id_role_thread states thread, " + str(e))
            time.sleep(connection_threads_sleep)

    def check_game_states_thread(self):
        """check conneciton to server periodically"""
        logger.info('Running check states thread')
        while True:
            try:
                self.reply_echo()
                self.check_turn_timeout()
                if self.opponent_disconnected_check():
                    break
            except Exception as e:
                logger.error("Exception on check states thread, " + str(e))

            time.sleep(connection_threads_sleep)

    def opponent_disconnected_check(self):
        state = self.connection.read_buffer('state', False)
        if state == cmd['state_types']['other_disconnected']:
            logger.info('Opponent disconnected, You won!')
            Game.game_ended = True
            return True

    def check_turn_timeout(self):
        isTimedOut = self.connection.read_buffer('timeout')
        if isTimedOut is True:
            logger.info('Turn timedout, next turn')
            Game.timed_out = True

    def confirm_role(self):
        """receive the role and send confirmation to the server"""
        id_role = self.connection.read_buffer('game_info')
        if id_role != '':
            self.id = id_role[0]
            self.role = id_role[1:]
            logger.info('Confirming role is: ' + str(self.role) +
                        ' and id is: ' + str(self.id))
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
            Game.timed_out = False
            board_content = self.connection.client_receive_with_wait('board')
            state = self.connection.client_receive_with_wait('state')

            if state == cmd['state_types']['your_turn']:
                self.print_board(board_content, 'input')
                self.get_player_move(board_content)

            else:
                self.print_board(board_content, 'empty')

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
            if Game.game_ended:
                break

    def print_board(self, board_content, board_type):
        if board_type == 'input':
            print('Current board:\n' +
                  self.format_board(self.convert_empty_board_position(board_content)))
        elif board_type == 'empty':
            print('Current board:\n' + self.format_board(board_content))

    def get_player_move(self, board_content):
        print('You have ' + str(TIMEOUT) + ' seconds.')
        end_time = int(round(time.time() * 1000)) + TIMEOUT
        while True:
            if Game.timed_out:
                break
            position = 0
            current_time = int(round(time.time() * 1000))
            try:
                choice = self.input_with_timeout(
                    end_time, current_time)
                if choice == 'q':
                    self.send_quit_signal()
                else:
                    position = int(choice)
                    if position >= 1 and position <= 9:
                        if board_content[position - 1] != " ":
                            logger.info(
                                'That postion is already taken. Please choose another')
                        else:
                            self.connection.client_send(
                                cmd['move'], str(position))
                            break
            except Exception:
                if Game.game_ended:
                    break
                logger.error('Expecting an integer number')
                pass

    def input_with_timeout(self, end_time, current_time):
        signal.signal(signal.SIGALRM,
                      self.press_enter_interrupt)
        signal.alarm(end_time - current_time)
        choice = self.input('Please enter the position (1~9):\n')
        signal.alarm(0)
        return choice

    def send_quit_signal(self):
        self.connection.client_send(
            cmd['quit'], '')
        logger.info('Exiting game')
        exit()

    def press_enter_interrupt(self, signum, frame):
        logger.info("interrupted")
        keyboard.release(Key.enter)

    def input(self, message):
        try:
            line = input(message)
            return line
        except:
            return
