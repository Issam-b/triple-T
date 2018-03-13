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

# command codenames between sever and client
commands = {
    'move': 'm',
    'quit': 'q',
    'echo': 'e',
    'confirm': 'c',
    'confirm_states': {
        'id received': '1',
        'role received': '2',
        'match received': '3' 
    },
    'lost': 'l',
    'win': 'w',
    'draw': 'd',
    'your_turn': 'u',
    'other_turn': 'o'
}

# setup logging file and format of log statement
logging.config.fileConfig('logging.conf')
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
                if(option.lower()) == 'n':
                    port = input('Enter new port number: ')
                    logger.info('New port specified: ' + str(port))
                    print('\n')
                elif(option.lower()) == 'q':
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
    active_players = [] # TODO: add logic to this
    players_count_history = 0

    def __init__(self, host, port):
        """Get the socket connection object from Server class."""
        Server.__init__(self)
        # bind to port number as integer
        self.bind_server(host, int(port))

    def start(self):
        """Start the game server."""
        # variable to keep track of connected clients
        self.__receive_connections()

    def __receive_connections(self):
        """show connected clients."""
        # get connection instances
        while True:
            conn, addr = self.server_socket.accept()
            logger.info('Connected to: ' + str(addr[0]) + ':' + str(addr[1]))
            try:
                new_player = Player(conn)
                cThread = threading.Thread(target=self.__client_handler, args=(new_player,))
                cThread.daemon = True             
                cThread.start()
                self.players_waitlist.append (new_player)
                logger.info('Total connected clients number is: ' + str(GameServer.players_count_history))
            except Exception as e:
                logger.error("Couldn't create a thread, terminating client session. Exception details: " + str(e))
                # close the current connection
                new_player.conn.send('e', 'Server error, terminating session')
                conn.close()

    def drop_player(self, player):
        """Disconnect a player or end connection with it"""
        logger.warning('Dropping player id: ' + str(player.id))
        player.second('Server ended your session.')
        player.conn.close()

    def __client_handler(self, player):
        """Thread to handle client connection."""
        # TODO: add clients connection logic, and players matching and game itself
        while True:

            mThread=threading.Thread(target=self.find_opponent, args=(player,))
            mThread.daemon = True
            mThread.start()
            received = player.receive(2, 'move')
            # if received is not None:
            #     player.send('move', '2')
            # if player.check_connection():
            #     break
            #create thread
            #check if there is more then 2
            #


    def find_opponent(self, player1):
        """find an opponenet for the player"""
        # TODO: implement this
        if len(self.players_waitlist) >= 2:
            for player2 in self.players_waitlist:
                player1.match = player2
                player2.match = player1
                player1.role= "X"
                player2.role = "O"


class PlayerPair:
    """class to arrage pairs of matched players"""

    def __init__(self, player1, player2):
        """init function for PlayerPair."""
        self.player1 = player1
        self.player2 = player2

class Player:
    """Player class to keep track of availble players and their status"""
    # count of players connected since the server started

    def __init__(self, conn):
        """called when new player created."""
        # update players count
        GameServer.players_count_history += 1
        self.conn = conn
        self.is_waiting = True
        self.id = self.__id_generator()
        logger.info('player with id: ' + str(self.id) + ' has joined.')
        self.role = None

    def send(self, command, msg):
        """Send data from server to player"""
        try:
            # TODO: add encryption
            self.conn.send((commands[command] + msg).encode())
            logger.info('sending: ' + str(command) + ' to: ' + str(self.id))
        except:
			# assume player is lost if an error accured
            self.__lost_connection()

    def receive(self, size, expected_command):
        """Receive data from player and check the validity of the data."""
        try:
            msg = self.conn.recv(size).decode()
            # TODO: add decryption
			# If received a quit signal from the client, print msg
            # TODO: ignore any command that is unknown
            if(len(msg) > 0 ):
                logger.info('received: ' + str(msg) + ' from: ' + str(self.id))
                if(msg[0] == commands['quit']):
                    logging.info(msg[1:])
                    self.__lost_connection()
                # If the message is not the expected type
                elif(msg[0] != commands[expected_command]):
                    # Connection lost
                    self.__lost_connection()
                # If received an integer from the client
                elif(msg[0] == commands['move']):
                    # Return the integer
                    return int(msg[1:])
                else:
                    return msg
        except Exception as e:
			# assume player connection is lost if received nothing
            logger.error('Got exception while receiving msg: ' + str(e))
            self.__lost_connection()
        return None

    def check_connection(self):
        """check if the player's connection is still alive, return true or false"""
        self.send(commands['echo'], 'f')
        if(self.receive(2, "e") == "f"):
            return True
        return False

    def __lost_connection(self):
        """Called when connection with player is lost"""
        logger.warning('Player: ' + str(self.id) + ' has lost connection!')
        # inform second player that his opponent has left the game
        # TODO: self.conn.send()

    def __id_generator(self, size = 4, chars = string.ascii_lowercase + string.digits):
        """Generate random id strings for the players, just for a unique id"""
        return ''.join(random.choice(chars) for _ in range(size))


def main():
    # If there are more than 2 arguments 
    if(len(argv) >= 2):
        # Set port number to argument 1
        port = argv[1]
    else:
        # get the port number to bind to
        port = input('Enter the port number: ')

    try:
        # start game server
        server = GameServer('', port).start()
        # close the socket connection before terminating the server
        server.close()

        logger.info('Exiting')
        exit(-1)

    except Exception as e:
        logger.error(str(e))

    
if __name__ == __name__:
    main()