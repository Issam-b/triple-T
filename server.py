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
message_length = 10
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
            try:
                self.server_socket.bind((host, int(port)))
                logger.info('Bind successful to port ' + str(port))
                self.server_socket.listen(5)
                logger.info('Listening on port ' + str(port))
                break

            except socket.error as e:
                logger.error("Got an error while connecting, " + str(e))
                exit(-1)

    def close(self):
        logger.info('Closing socket')
        self.server_socket.close()

class GameServer(Server):
    """Handle game start and clients management."""

    players_waitlist = []
    active_players = []
    players_count_history = 0
    active_games = []

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
        matchingThread = threading.Thread(target=self.find_opponent, args=(), daemon=True).start()

        # get connection instances
        while True:
            conn, addr = self.server_socket.accept()
            logger.info('Connected to: ' + str(addr[0]) + ':' + str(addr[1]))
            try:
                new_player = Player(conn)
                # recvThread = threading.Thread(target=self.player_receive_daemon, args=(new_player,), daemon=True).start()

                connThread = threading.Thread(target=self.player_check_connection, args=(new_player,), daemon=True).start()
                
                GameServer.players_waitlist.append(new_player)
                GameServer.active_players.append(new_player)
                logger.info('Waiting players: ' + str(len(GameServer.players_waitlist)))
                logger.info('Active online players are: ' + str(len(GameServer.active_players)))
                logger.info('Number of all served players is: ' + str(GameServer.players_count_history))

            except Exception as e:
                logger.error("Couldn't create a thread, terminating client session. Exception details: " + str(e))
                conn.close()

    def drop_player(self, player):
        """Disconnect a player or end connection with it"""
        logger.warning('Dropping player id: ' + str(player.id))
        if player.is_waiting is False:
            game = self.get_game(player)
            opponent = self.get_opponent(player)
            if opponent is not None:
                # inform opponent then drop it from server lists
                opponent.send(commands['state'], commands['state_types']['other_disconnected'])
                if game in self.active_games:
                    self.active_games.remove(game)
                

        if player in GameServer.players_waitlist:
            GameServer.players_waitlist.remove(player)
        if player in GameServer.active_players:
            GameServer.active_players.remove(player)
            
        player.conn.close()

    def player_receive_daemon(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info('Running receive thread on player: ' + str(player.id))
        while True:
            if player.disconected:
                break
            player.receive_populate_buffer()
            time.sleep(1)

    def player_check_connection(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info('Running connection check thread on player: ' + str(player.id))
        while True:
            challenge = 'f'
            player.send(commands['echo'], challenge)
            player.receive_populate_buffer()
            echo_value = player.read_buffer('echo')
            quit_cmd = player.read_buffer('quit')
           
            if quit_cmd or player.disconected or echo_value != challenge:
                if quit_cmd:
                    logger.warning('Player: ' + str(player.id) + ' asked to quit')

                self.drop_player(player)
                break

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
                        gameThread = threading.Thread(target=self.game_thread, args=(player1, player2), daemon=True).start()
                        player1.is_waiting = False
                        player2.is_waiting = False
                    except Exception as e:
                        logger.error('could not create game thread, exception message: ' + str(e))

                else:
                    if not player1_send and  not player2_send:
                        if {player1, player2} in GameServer.players_waitlist:
                            GameServer.players_waitlist.remove(player2)
                            GameServer.players_waitlist.remove(player1)
                    else:
                        if player1_send is True:
                            if player2 in GameServer.players_waitlist:
                                GameServer.players_waitlist.remove(player2)
                            player1.send(commands['state'], commands['state_types']['other_disconnected'])
                        if player2_send is True:
                            if player1 in GameServer.players_waitlist:
                                GameServer.players_waitlist.remove(player1)
                            player2.send(commands['state'], commands['state_types']['other_disconnected'])

            time.sleep(1)

    def get_opponent(self, player):
        """return opponnet player object of a player"""
        game = self.get_game(player)
        if game is not None:
            if player == game.player1:
                return game.player2
            else:
                return game.player1
        else:
            return None


    def get_game(self, player):
        """return an object game related to a player"""
        for game in self.active_games:
            if player in {game.player1, game.player2}:
                return game
            else:
                return None

    def game_thread(self, player1, player2):
        """start a new game in seperate thread"""
        try:
            new_game = Game(player1, player2)
            self.active_games.append(new_game)
            new_game.start()

        except Exception as e:
            logger.error('Game ended unexpectedly, ' + str(e))


class Game:
    """The game logic, moves, win and lose events handler"""

    def __init__(self, player1, player2):
        """initiate the game"""
        logger.info('Matched player: ' + str(player1.id) + ' with opponenet: ' + str(player1.opponenet))
        self.player1 = player1
        self.player2 = player2
        self.moves_counter = 0
        self.state = ''
        self.board = list('         ')

    def start(self):
        """start the current game"""
        logger.info('Starting the game between: ' + str(self.player1.id) + ' and: ' + str(self.player2.id))
        while True:
            # alternate moves between players
            if self.move(self.player1, self.player2):
                return
            if self.move(self.player2, self.player1):
                return

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

        try:
            # Receive the move from the moving player
            move = int(moving_player.receive('move'))
            # Check if the position is empty
            if self.board[move - 1] == " ":
                # Write the move into the board
                self.board[move - 1] = moving_player.role
                self.moves_counter += 1
            else:
                logging.warning("Player " + str(moving_player.id) + " wants to take a taken position")
        except Exception as e:
            logger.error('Expected an integer move')
            raise
        # Check if this will result in a win
        if self.moves_counter > 4:
            result, winning_path = self.check_winner(moving_player)
            if (result >= 0):
                # Send back the latest board content
                moving_player.send(commands['board'], ("".join(self.board)))
                waiting_player.send(commands['board'], ("".join(self.board)))

                if (result == 0):
                    # If this game ends with a draw, send the players the result
                    moving_player.send(commands['state'], commands['state_types']['draw'])
                    waiting_player.send(commands['state'], commands['state_types']['draw'])
                    logger.info('Game between player ' + str(moving_player.id) + ' and '
                        + str(waiting_player.id) + ' ended with a draw.')
                    return True
                if (result == 1):
                    # Send the players the result if current player wins
                    moving_player.send(commands['state'], commands['state_types']['win'])
                    waiting_player.send(commands['state'], commands['state_types']['lose'])

                    logger.info('Player ' + str(moving_player.id) + ' beated player ' + str(waiting_player.id))
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
        # self.id = self.id_generator()
        self.id = GameServer.players_count_history
        logger.info('player with id: ' + str(self.id) + ' has joined.')
        self.role = ''
        self.opponenet = ''
        self.disconected = False
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
            # logger.info('sending: ' + str(command + msg) + ' to: ' + str(self.id))
        except Exception as e:
			# assume player connection is lost if an error accured
            self.lost_connection()

    def receive_populate_buffer(self, size=message_length):
        """receive commands and save to buffer untill read by server"""
        try:
            self.conn.settimeout(5.0)
            msg = self.conn.recv(size).decode()
            # TODO: add decryption
            if len(msg) > 0:
                # logger.info('received: ' + str(msg) + ' from: ' + str(self.id))
                recv_cmd = ''

                items = commands.items()
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

    def receive(self, expected_command):
        """Receive data from player and check the validity of the data."""
        
        # fetch data
        while self.cmd_buffer[str(expected_command)] == '' and not self.disconected:
            # self.receive_populate_buffer()
            time.sleep(1)

        # read buffer and save value needed
        cmd_to_return = self.cmd_buffer[str(expected_command)]
        self.cmd_buffer[str(expected_command)] = ''

        return cmd_to_return

    def read_buffer(self, expected_command):
        """read the current data from buffer"""
        return self.cmd_buffer[str(expected_command)]

    def send_game_info(self):
        """send the player his assigned role and matched opponenet."""
        # send game info to player
        counter = 0
        success_state = False
        msg = str(self.role)
        logger.info('Sending game info to: ' + str(self.id))
        # tries to send for two times if having an error at first
        self.send(commands['game_info'], msg)  
        try:
            if int(self.receive('confirm')) != int(commands['confirm_states']['game_info_received']):
                self.lost_connection()
                # on no confirmation remove player server lists since it's disconnected
                if self in GameServer.players_waitlist:
                    GameServer.players_waitlist.remove(self)
                if self in GameServer.active_players:
                    GameServer.active_players.remove(self)
            else:
                # sent and receive successful
                if self in GameServer.players_waitlist:
                    GameServer.players_waitlist.remove(self)
                success_state = True

        except Exception as e:
            logger.error('Expected a valid integer, exception message: ' + str(e))
        
        return success_state

    def lost_connection(self):
        """Called when connection with player is lost"""
        self.disconected = True
        logger.warning('Player: ' + str(self.id) + ' has lost connection!')

    def id_generator(self, size=4, chars=string.ascii_lowercase + string.digits):
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