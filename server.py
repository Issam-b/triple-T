#! /usr/bin/python3

# socket module
import socket
# argv from sys module to get arguments
from sys import argv
# logging module to log events to file
import logging
import logging.config
import threading
import string
import random
import time
from configparser import ConfigParser

# command codenames between sever and client
message_length = 2
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

# setup logging file and format of log statement
logging.config.fileConfig('settings.conf')
logger = logging.getLogger('server')

class Server:
    """Server class to handle connection related calls."""

    def __init__(self):
        """Initializes the server object with a server socket."""
		# create the TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def bind_server(self, host, port):
        """bind and listen to the the given port."""

        while True:
            # try to bind
            try:
                self.server_socket.bind((host, int(port)))
                logger.info('Bind successful to port ' + str(port))
                self.server_socket.listen(5)
                logger.info('Listening on port ' + str(port))
                break

            except socket.error as e:
                # print errors
                logger.error(str(e))

                # show menu
                option = input('Choose an option:\n[N]ew port | [Q]uit : ')

                # assign new port or exit
                if option.lower() == 'n':
                    port = input('Enter new port number: ')
                    logger.info('New port specified: ' + str(port))
                    print('\n')
                elif option.lower() == 'q':
                    logger.info('Exit the program!')
                    exit(0)
                else:
                    logger.error('Bad choice, exit!')
                    exit(-1)

    def close(self):
        logger.info('Closing socket')
        self.server_socket.close()

class GameServer(Server):
    """Handle game start and clients management."""

    players_waitlist = []
    active_players = []
    players_count_history = 0

    def __init__(self, host, port):
        """Get the socket connection object from Server class."""
        Server.__init__(self)
        # bind to port number as integer
        self.bind_server(host, int(port))

    def start(self):
        """Start the game server."""
        self.__receive_connections()

    def __receive_connections(self):
        """show connected clients."""

        # variable to keep track of connected clients
        matchingThread = threading.Thread(target=self.find_opponent, args=())
        matchingThread.daemon = True
        matchingThread.start()

        # get connection instances
        while True:
            conn, addr = self.server_socket.accept()
            logger.info('Connected to: ' + str(addr[0]) + ':' + str(addr[1]))
            try:
                new_player = Player(conn)
                # cThread = threading.Thread(target=self.check_player_connection, args=(new_player,))
                # cThread.daemon = True             
                # cThread.start()
                GameServer.players_waitlist.append(new_player)
                GameServer.active_players.append(new_player)
                logger.info('length of waitlist: ' + str(len(GameServer.players_waitlist)))
                logger.info('Total active connected clients number is: ' + str(len(GameServer.active_players)))
                logger.info('Number of served clients since server start is: ' + str(GameServer.players_count_history))

            except Exception as e:
                logger.error("Couldn't create a thread, terminating client session. Exception details: " + str(e))
                # close the current connection
                new_player.conn.send('e', 'Server error, terminating session')
                conn.close()

    def drop_player(self, player):
        """Disconnect a player or end connection with it"""
        logger.warning('Dropping player id: ' + str(player.id))
        if player.is_waiting is False:
            opponent = Game.get_opponent(player)
            if opponent is not None:
                opponent.send(commands['win'])
        # TODO: if player is in a game, inform the other player

        if self in GameServer.players_waitlist:
            GameServer.players_waitlist.remove(player)
            print('dropping wait')
        if self in GameServer.active_players:
            GameServer.active_players.remove(player)
            print('dropping active')
        # close the player's connection
        player.conn.close()

    def check_player_connection(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info('Running connection check thread on player: ' + str(player.id))
        while True:
            if player.check_connection() is False:
                        self.drop_player(player)
            time.sleep(1)

    def find_opponent(self):
        """find an opponenet for the player"""
        while True:
            if len(self.players_waitlist) > 1:
                logger.info('Matching players from waitlist')
                player1 = GameServer.players_waitlist[0]
                player2 = GameServer.players_waitlist[1]
                player1.match = player2
                player2.match = player1
                # assign role in the game
                player1.role= "X"
                player2.role = "O"
                player1.opponenet = player2.id
                player2.opponenet = player1.id
                # send the players game info
                player1_send = player1.send_game_info()
                player2_send = player2.send_game_info()
                if player1_send is True and player2_send is True:
                    try:
                        gameThread = threading.Thread(target=self.game_thread, args=(player1, player2))
                        gameThread.daemon = True
                        gameThread.start()
                        player1.is_waiting = False
                        player2.is_waiting = False
                    except Exception as e:
                        logger.error('could not create game thread, exception message: ' + str(e))

                else:
                    if player1_send is True and player2_send is False:
                        GameServer.players_waitlist.append(player1)
                        # TODO: send other player that his opponent is disconnected
                    if player2_send is True and player1_send is False:
                        GameServer.players_waitlist.append(player2)
                        # TODO: send other player that his opponent is disconnected

            # wait for 1 second
            time.sleep(1)

    def game_thread(self, player1, player2):
        """start a new game in seperate thread"""
        try:
            new_game = Game(player1, player2)
            new_game.start()
        except Exception as e:
            logger.error('Game ended unexpectedly, exception message: ' + str(e))
            # TODO: send other player that his opponent disconected


class Game:
    """The game logic, moves, win and lose events handler"""

    def __init__(self, player1, player2):
        """initiate the game"""
        logger.info('Matched player: ' + str(player1.id) + ' with opponenet: ' +
            str(player1.opponenet) + ' the role of: ' + str(player1.role))
        self.player1 = player1
        self.player2 = player2
        self.moves_counter = 0
        self.state = ''
        self.board = list('         ')

    def start(self):
        """start the current game"""
        logger.info('Starting the game between: ' + str(self.player1.id) + ' and: ' + str(self.player2.id))
        while True:
            # move players
            if self.move(self.player1, self.player2) is True:
                return
            if self.move(self.player2, self.player1) is True:
                return

    def get_opponent(self, player):
        """return the game objet of a player"""
        if player == self.player1:
            return self.player2
        elif player == self.player2:
            return self.player1
        else:
            return None

    def move(self, moving_player, waiting_player):
        """move the players by turn"""
        # Send both players the current board
        board_content = "".join(self.board)
        moving_player.send(commands['board'], board_content)
        waiting_player.send(commands['board'], board_content)
        # Let the moving_player move, "your_turn" stands for yes it's turn to move,
        # "other_turn" stands for no and waiting
        moving_player.send(commands['state'], commands['state_types']['your_turn'])
        waiting_player.send(commands['state'], commands['state_types']['other_turn'])

        # Receive the move from the moving player
        move = int(moving_player.read_buffer('move'))
        # Send the move to the waiting player
        # waiting_player.send(commands['board'], str(move))
        # Check if the position is empty
        if self.board[move - 1] == " ":
            # Write the it into the board
            self.board[move - 1] = moving_player.role
            self.moves_counter += 1
        else:
            logging.warning("Player " + str(moving_player.id) + 
            " is attempting to take a position that's already been taken.")
        # Check if this will result in a win
        if self.moves_counter > 4:
            result, winning_path = self.check_winner(moving_player)
            if (result >= 0):
                # If there is a result
                # Send back the latest board content
                moving_player.send(commands['board'], ("".join(self.board)))
                waiting_player.send(commands['board'], ("".join(self.board)))

                if (result == 0):
                    # If this game ends with a draw
                    # Send the players the result
                    moving_player.send(commands['state'], commands['state_types']['draw'])
                    waiting_player.send(commands['state'], commands['state_types']['draw'])
                    logger.info('Game between player ' + str(moving_player.id) + ' and player '
                        + str(waiting_player.id) + ' ended with a draw.')
                    return True
                if (result == 1):
                    # If this player wins the game
                    # Send the players the result
                    moving_player.send(commands['state'], commands['state_types']['win'])
                    waiting_player.send(commands['state'], commands['state_types']['lose'])
                    # # Send the players the winning path
                    # moving_player.send('p', winning_path)
                    # waiting_player.send('p', winning_path)
                    logger.info('Player ' + str(moving_player.id) + ' beated player '
                        + str(waiting_player.id))
                    return True
                return False

    def check_winner(self, player):
        """Checks if the player wins the game. Returns 1 if wins,
        0 if it's a draw, -1 if there's no result yet."""
        s = self.board

        # Check columns
        if (len(set([s[0], s[1], s[2], player.role])) == 1):
            return 1, "012"
        if (len(set([s[3], s[4], s[5], player.role])) == 1):
            return 1, "345"
        if (len(set([s[6], s[7], s[8], player.role])) == 1):
            return 1, "678"

        # Check rows
        if (len(set([s[0], s[3], s[6], player.role])) == 1):
            return 1, "036"
        if (len(set([s[1], s[4], s[7], player.role])) == 1):
            return 1, "147"
        if (len(set([s[2], s[5], s[8], player.role])) == 1):
            return 1, "258"

        # Check diagonal
        if (len(set([s[0], s[4], s[8], player.role])) == 1):
            return 1, "048"
        if (len(set([s[2], s[4], s[6], player.role])) == 1):
            return 1, "246"

        # If there's no empty position left, draw
        if " " not in s:
            return 0, ""

        # The result cannot be determined yet
        return -1, ""


class Player:
    """Player class to keep track of availble players and their status"""
    # count of players connected since the server started

    def __init__(self, conn):
        """called when new player created."""
        # update players count
        GameServer.players_count_history += 1
        self.conn = conn
        self.is_waiting = True
        # self.id = self.__id_generator()
        self.id = GameServer.players_count_history
        logger.info('player with id: ' + str(self.id) + ' has joined.')
        self.role = ''
        self.opponenet = ''
        self.cmd_buffer = {
            'move': '',
            'board': '',
            'quit': '',
            'echo': '',
            'confirm': '',
            'state': '',
            'game_info': ''
        }

    def send(self, command, msg):
        """Send data from server to player"""
        try:
            # TODO: add encryption
            self.conn.send((command + msg).encode())
            # logger.info('sending: ' + str(command) + ' to: ' + str(self.id))
        except:
			# assume player is lost if an error accured
            self.__lost_connection()

    # TODO: add function to handle checking and receiveing

    def receive_populate_buffer(self, size=message_length):
        """receive commands and save to buffer untill read by server"""
        try:
            msg = self.conn.recv(size).decode()
            # TODO: add decryption
			# If received a quit signal from the client, print msg
            if len(msg) > 0:
                logger.info('received: ' + str(msg) + ' from: ' + str(self.id))
                recv_cmd = ''
                if size == 10:
                    self.cmd_buffer['board'] = msg[1:]
                else:
                    items = commands.items()
                    for key, cmd in items:
                        if cmd == msg[0]:
                            recv_cmd = key
                            break

                    # cmd_type_1 = {'quit', 'lose', 'win', 'your_turn', 'other_turn'}
                    # cmd_type_2 = {'echo', 'move', 'confirm', 'state'}

                    # if recv_cmd in cmd_type_1:
                    #     self.cmd_buffer[str(recv_cmd)] = True
                    # elif recv_cmd in cmd_type_2:
                    self.cmd_buffer[str(recv_cmd)] = msg[1:]

        except Exception as es:
            logger.error('Got exception while receiving msg: ' + str(es))

    def read_buffer(self, expected_command):
        """Receive data from player and check the validity of the data."""
        # TODO put each player in a seperate thread
        # fetch data
        if expected_command == 'board':
            self.receive_populate_buffer(10)
        else:
            self.receive_populate_buffer()

        # read buffer and save value needed
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        # clear it after reading it
        # self.cmd_buffer[str(expected_command)] = ''

        return cmd_to_return

        # if msg[0] == commands['quit']:
        #     # logging.info(msg[1:])
        #     logger.warning('Player: ' + str(self.id) + ' asked to quit')
        #     self.conn.close()
        #     GameServer.drop_player(self)
        #     # self.__lost_connection()

        # # echo command
        # elif msg[0] == commands['echo']:
        #     return 
        # # If the message is not the expected type
        # elif msg[0] != expected_command:
        #     # Connection lost
        #     # self.__lost_connection()
        #     logger.warning('Received unexpected message')
        # # If received an integer from the client
        # elif msg[0] == commands['move']:
        #     # Return the integer
        #     return int(msg[1:])
        # else:
        #     return msg[1:]
        # return msg

    def check_connection(self):
        """check if the player's connection is still alive, return true or false"""
        # challenge = Player.__id_generator(1)
        challenge = 'f'
        self.send(commands['echo'], challenge)
        if self.read_buffer('echo') == challenge:
            return True
        else:
            self.__lost_connection()
            return False

    def send_game_info(self):
        """send the player his assigned role and matched opponenet."""
        # send game info to player
        counter = 0
        # msg = str(self.role + self.opponenet)
        msg = str(self.role)
        while True:
            self.send(commands['game_info'], msg)
            # tries to send for two times
            logger.info('Sending game info to: ' + str(self.id) + ' for ' + str(counter) + ' time')
            try:
                counter += 1
                if counter < 2:
                    # TODO: fix flood of error
                    if int(self.read_buffer('confirm')) != int(commands['confirm_states']['game_info_received']):
                        # if counter == 2 and self.check_connection() is False:
                    
                        # try again to check if player is connected
                        self.__lost_connection()
                        # remove player from our lists
                        if self in GameServer.players_waitlist:
                            GameServer.players_waitlist.remove(self)
                        if self in GameServer.active_players:
                            GameServer.active_players.remove(self)
                        # return false
                        return False
                        # TODO: send other guy that opponnent is disconnected
                        
                    else:
                        # sent and receive successful
                        if self in GameServer.players_waitlist:
                            GameServer.players_waitlist.remove(self)
                        return True
                else:
                    logger.warning('Player: ' + str(self.id) + ' did not confirm receiving, try second time')
            except Exception as e:
                logger.error('Expected a valid integer, exception message: ' + str(e))

    def __lost_connection(self):
        """Called when connection with player is lost"""
        logger.warning('Player: ' + str(self.id) + ' has lost connection!')
        # GameServer.drop_player(self)
        # TODO: delete instance
        # inform second player that his opponent has left the game
        # remove the player from our lists
        # TODO: self.conn.send()

    def __id_generator(self, size=4, chars=string.ascii_lowercase + string.digits):
        """Generate random id strings for the players, just for a unique id"""
        return ''.join(random.choice(chars) for _ in range(size))


def main():
    # get configuration
    config = ConfigParser()
    config.read('settings.conf')
    port = config.get('connection', 'port')

    try:
        # start game server
        server = GameServer('', int(port)).start()
        # close the socket connection before terminating the server
        server.close()

        logger.info('Exiting')
        exit(-1)

    except Exception as e:
        logger.error(str(e))


if __name__ == __name__:
    main()