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

# command codenames between sever and client
commands = {
    'move': { 'cmd': 'm', 'len': '2'},
    'quit': 'q',
    'echo': { 'cmd': 'e', 'len': '2'},
    'confirm': { 'cmd': 'c', 'len': '2'},
    'confirm_states': {
        'id_received': '1',
        'game_info_received': '2',
    },
    'lose': { 'cmd': 'l', 'len': '1'},
    'win': { 'cmd': 'w', 'len': '1'},
    'draw': { 'cmd': 'd', 'len': '1'},
    'your_turn': { 'cmd': 'u', 'len': '1'},
    'other_turn': { 'cmd': 'o', 'len': '1'},
    'game_info': { 'cmd': 'g', 'len': '6'}
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
    active_players = []
    players_count_history = 0

    def __init__(self, host, port):
        """Get the socket connection object from Server class."""
        Server.__init__(self)
        # bind to port number as integer
        self.bind_server(host, int(port))
        matchingThread = threading.Thread(target=self.find_opponent(), args=())
        matchingThread.daemon = True             
        matchingThread.start()

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
                # cThread = threading.Thread(target=self.__client_handler, args=(new_player,))
                # cThread.daemon = True             
                # cThread.start()
                self.players_waitlist.append(new_player)
                self.active_players.append(new_player)
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

    # def __client_handler(self, player):
    #     """Thread to handle client connection."""
    #     while True:

    #         mThread=threading.Thread(target=self.find_opponent, args=(player,))
    #         mThread.daemon = True
    #         mThread.start()
    #         received = player.receive(2, 'move')
    #         # if received is not None:
    #         #     player.send('move', '2')
    #         # if player.check_connection():
    #         #     break
    #         #create thread
    #         #check if there is more then 2
    #         #


    def find_opponent(self):
        """find an opponenet for the player"""
        while len(self.players_waitlist) > 1:
            logger.info('Matching players from waitlist')
            player1 = self.players_waitlist[0]
            player2 = self.players_waitlist[1]
            player1.match = player2
            player2.match = player1
            # assign role in the game
            player1.role= "X"
            player2.role = "O"
            # send the players game info
            player1_send = player1.send_game_info()
            player2_send = player2.send_game_info()
            if player1_send and player2_send:
                try:
                    gameThread = threading.Thread(target=self.game_thread, args=(player1, player2))
                    gameThread.daemon = True
                    gameThread.start()
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


class Game:
    """The game logic, moves, win and lose events handler"""

    def __init__(self, player1, player2):
        """initiate the game"""
        logger.info('Matched player: ' + str(player1.id) + ' with opponenet: ' +
            str(player1.opponenet) + ' the role of: ' + str(player1.role)) 
        self.player1 = player1
        self.player2 = player2
        self.board = list('         ')

    def start(self):
        """start the current game"""
         logger.info('Starting the game between: ' + str(new_game.player1.id) + ' and: ' + str(new_game.player2.id))
        # move players
        if(self.move(self.player1, self.player2))
            return
        if(self.move(self.player1, self.player2))
            return

    def move(self, player1, player2):
        """move the players by turn"""
        # TODO: implement move and win and lose

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
        self.opponenet = None

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

    def send_game_info(self):
        """send the player his assigned role and matched opponenet."""
        # send game info to player
        counter = 0
        msg = str(self.role + self.opponenet)
        while True:
            self.send(commands['game_info'], msg)
            # tries to send for two times
            counter += 1
            logger.info('Sending game info to: ' + str(self.id) + ' for ' + counter + ' time')
            if self.receive(commands['confirm']['len'], commands['confirm']) != commands['confirm_states']['game_info_received'] and counter == 2:
                if self.check_connection() is not False:
                    # try again to check if player is connected
                    self.__lost_connection()
                    # remove player from our lists
                    GameServer.players_waitlist.remove(self)
                    GameServer.active_players.remove(self)
                    # return false
                    return False
                    # TODO: send other guy that opponnent is disconnected
            else:
                # sent and receive successful
                logger.warning('Player: ' + str(self.id) + 'did not confirm receiving')
                GameServer.players_waitlist.remove(self)
                return True

    def __lost_connection(self):
        """Called when connection with player is lost"""
        logger.warning('Player: ' + str(self.id) + ' has lost connection!')
        # inform second player that his opponent has left the game
        # remove the player from our lists
        GameServer.players_waitlist.remove(self)
        GameServer.active_players.remove(self)
        # TODO: self.conn.send()

    def __id_generator(self, size = 4, chars = string.ascii_lowercase + string.digits):
        """Generate random id strings for the players, just for a unique id"""
        return ''.join(random.choice(chars) for _ in range(size))


def main():
    try:
        # start game server
        server = GameServer('', 8080).start()
        # close the socket connection before terminating the server
        server.close()

        logger.info('Exiting')
        exit(-1)

    except Exception as e:
        logger.error(str(e))

    
if __name__ == __name__:
    main()