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
        'other_turn': 'o'
    },
    'board': 'b',
    'game_info': 'g'
}


class ClientConnection():
  """class to handle connection to server, receive and send"""
  # default values
  message_length = 2
  # buffer for received data
  cmd_buffer = {
            'move': '',
            'board': '',
            'quit': '',
            'echo': '',
            'confirm': '',
            'state': '',
            'game_info': ''
  }

  def __init__(self):
    """ini the class objects"""
    # Create the socket object
    # 1st parameter: IPv4 networking
    # 2nd parameter: socket type, SOCK_STREAM = TCP
    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
      # TODO: add decryption
      # if message is not empty procceed
      if len(msg) > 0:
        recv_cmd = ''
        # if msg size 10 it's meant for the board
        if size == 10:
          self.cmd_buffer['board'] = msg[1:]
        # put other type of message in the appropriate field
        else:
          items = commands.items()
          for key, cmd in items:
            if cmd == msg[0]:
              recv_cmd = key
              break
          # save received message to buffer
          self.cmd_buffer[str(recv_cmd)] = msg[1:]

    except Exception as e:
      logger.error("Error receiveing from buffer, exception message: " + str(e))

  def client_receive(self, expected_command):
      """Receive data from player and check the validity of the data."""
      # TODO put each player in a seperate thread
      # fetch data
      if expected_command == 'board':
          self.receive_populate_buffer(10)
      else:
          self.receive_populate_buffer()

      # read buffer and save value needed
      cmd_to_return = self.cmd_buffer[str(expected_command)]
      logger.info('Received: ' + str(cmd_to_return))
      return cmd_to_return

  def client_send(self, cmd, msg):
      """Send data from server to player"""
      try:
          # TODO: add encryption
          # logger.info('Sending: ' + str(cmd + msg))
          self.client_socket.send((cmd + msg).encode())

      except:
        # assume player is lost if an error accured
        self.connection_lost()

  def check_connection(self):
    """reply to the server that the conneciton is still active"""
    # Send echo response
    msg = self.client_receive('echo')
    # logger.info('Received an echo request: ' + str(msg))
    if msg == 'f':
      self.client_send('echo', msg)

  def confirm_role(self):
    """receive the role and send confirmation to the server"""
    # wait for match
    msg = self.client_receive('game_info')
    if msg != '':
      logger.info('player role is: ' + str(msg))
      self.client_send('c', '1')

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
  
  def __init__(self, connection):
    """init function for game"""
    self.connection = connection
    # create connection to server
    self.connection.client_connect()
    # receive role from server
    self.connection.confirm_role()

  def convert_empty_board_position(self, board):
    """Convert board into readable board with X and O"""
    new_board = list("123456789")
    for i in range(0, 9):
      if board[i] != ' ':
        new_board[i] = board[i]
    return "".join(new_board)

  def format_board(self, board):
    """return the board values formatted to print"""
    if(len(board) != 9):
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
      opponent_position = 0
      state = self.connection.client_receive('state')

      # If it's this player's turn to move
      if state == commands['state_types']['your_turn']:
        # Print out the current board with " " converted to the position number
        print('Current board:\n' + self.format_board(self.convert_empty_board_position(board_content)))
        while True:
          position = int(input('please enter the postion (1~9): '))
          if (position >= 1 and position <= 9):
            if (board_content[position - 1] != " "):
              logger.info('That postion is already taken. Please choose another')
            else:
              self.connection.client_send(commands['move'], str(position))
              break
      else:
        # Print out the current board
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