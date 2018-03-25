#! /usr/bin/python3

# Import the socket module
import socket
# Import command line arguments
from sys import argv
from configparser import ConfigParser
import time
# setup logging file and format of log statement
import logging
import logging.config
import threading
import ssl

CERT = 'server_cert.pem'

logging.config.fileConfig('settings.conf')
logger = logging.getLogger('client')

commands = {
    'move': 'm',
    'quit': 'q',
    'echo': 'e',
    'confirm': 'c',
    'confirm_states': {
        'game_info_received': '1',
        'id_received': '2'
    },
    'state': 's',
    'state_types': {
        'lose': 'l',
        'win': 'w',
        'draw': 'd',
        'your_turn': 'u',
        'other_turn': 'o',
        'other_disconnected': 'z'
    },
    'board': 'b',
    'game_info': 'g'
}


class ClientConnection():
    """class to handle connection to server, receive and send"""
    # default values
    message_length = 10
    # buffer for received data
    cmd_buffer = {
        'move': '',
        'board': '',
        'quit': '',
        'echo': '',
        'confirm': '',
        'state': '',
        'game_info': '',
    }

    def __init__(self):
        """ini the class objects"""
        # Create the socket object
        # 1st parameter: IPv4 networking
        # 2nd parameter: socket type, SOCK_STREAM = TCP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def client_connect(self):
        """connect to server function"""
        while True:
            try:
                # get configuration
                config = ConfigParser()
                config.read('settings.conf')
                address = config.get('connection', 'address')
                port = config.get('connection', 'port')

                # Connect to host address, port
                logger.info("Trying to Connect Server...")
                # use connection with ssl wrapped socket
                self.client_socket = ssl.wrap_socket(self.socket, cert_reqs=ssl.CERT_REQUIRED, ca_certs=CERT)
                self.client_socket.connect((address, int(port)))
                logger.info("Connected to Server")

                break
            except Exception as e:
                logger.error('Error connecting, exception message: ' + str(e))
            finally:
                time.sleep(1)

    def receive_populate_buffer(self, size=message_length):
        """receive commands and save to buffer untill read by server"""
        try:
            msg = self.client_socket.recv(size).decode()

            if len(msg) > 0:
                # logger.info('received: ' + str(msg))
                recv_cmd = ''

                items = commands.items()
                for key, cmd in items:
                    if cmd == msg[0]:
                        recv_cmd = key
                        break

                if recv_cmd == 'board':
                    self.cmd_buffer[str(recv_cmd)] = msg[1:]
                else:
                    self.cmd_buffer[str(recv_cmd)] = msg[1]

        except Exception as es:
            logger.error('Got exception while receiving msg: ' + str(es))

    def client_receive(self, expected_command, clear=True):
        """Receive data from player and check the validity of the data."""
         
        # fetch data
        while self.cmd_buffer[str(expected_command)] == '':
            # self.receive_populate_buffer()
            if Game.game_ended:
                break
            time.sleep(0.1)

        # read buffer and save value needed
        return self.read_buffer(expected_command, clear)

    def read_buffer(self, expected_command, clear=True):
        """read the current data from buffer"""
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        if clear:
            self.cmd_buffer[str(expected_command)] = ''

        return cmd_to_return

    def client_send(self, cmd, msg):
        """Send data from server to player"""
        try:
            # logger.info('Sending: ' + str(cmd + msg))
            self.client_socket.send((cmd + msg).encode())

        except Exception as e:
            # assume player is lost if an error accured
            self.connection_lost()

    def connection_lost(self):
        """called when connection is lost"""
        logger.error('Connection lost!')
        raise

    def close(self):
        """close the connection"""
        # Shut down the socket (prevent more send/rec)
        self.client_socket.shutdown(socket.SHUT_RDWR)
        # Close Socket
        self.client_socket.close()


class Game():
    """handle gameplay logic"""
  
    game_ended = False
    def __init__(self, connection):
        """init function for game, connect to server and start receive threads"""
        self.game_started = False
        self.connection = connection
        self.connection.client_connect()

        checkConnThread = threading.Thread(target=self.check_states, args=(), daemon=True).start()
        fetchThread = threading.Thread(target=self.fetch_data, args=(), daemon=True).start()

    def fetch_data(self):
        """fetch data from server periodically"""
        while True:
            self.connection.receive_populate_buffer()
            if Game.game_ended:
                break
            # time.sleep(0.5)

    def check_states(self):
        """check conneciton to server periodically"""
        logger.info('Running connection check thread')
        while True:
            try:
                
                self.reply_echo()
                if not self.game_started:
                    # TODO get player id
                    self.confirm_role()

                else:
                    state = self.connection.read_buffer('state', False)
                    if state == commands['state_types']['other_disconnected']:
                        logger.info('Opponent disconnected, You won!')
                        Game.game_ended = True
                        break
                
            except Exception as e:
                logger.error("Exception on check states thread, " + str(e))

            time.sleep(0.5)

    def confirm_role(self):
        """receive the role and send confirmation to the server"""
        role = self.connection.read_buffer('game_info')
        if role != '':
            logger.info('Confirming player role is: ' + str(role))
            self.connection.client_send(commands['confirm'], commands['confirm_states']['game_info_received'])
            self.game_started = True

    def reply_echo(self):
        """reply to the server that the conneciton is still active"""
        echo_value = self.connection.read_buffer('echo')
        if echo_value != '':
            self.connection.client_send(commands['echo'], echo_value)

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
            if state == commands['state_types']['your_turn']:
                # Print out the current board with " " converted to the position number
                print('Current board:\n' + self.format_board(self.convert_empty_board_position(board_content)))
                while True: 
                    position = 0
                    try:
                        choice = input('please enter the postion (1~9): ')
                        if choice == 'q':
                            self.connection.client_send(commands['quit'], '')
                            logger.info('Exiting game')
                            exit()
                        else:
                            position = int(choice)
                    except Exception as e:
                        if Game.game_ended:
                            break   
                        logger.error('Expecting an integer number')
                        pass
                    if position >= 1 and position <= 9:
                        if board_content[position - 1] != " ":
                            logger.info('That postion is already taken. Please choose another')
                        else:
                            self.connection.client_send(commands['move'], str(position))
                            break
            else:
                print('Current board:\n' + self.format_board(board_content))

                if state == commands['state_types']['other_turn']:
                    logger.info("Waiting for the other player to make a move")

                elif state == commands['state_types']['draw']:
                    logger.info("It's a draw.")
                    break

                elif state == commands['state_types']['win']:
                    logger.info("You WIN!")
                    break

                elif state == commands['state_types']['lose']:
                    logger.info("You lose.")
                    break


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