#! /usr/bin/python3

import threading
import time
from helpers import setup_logger
from server import Server
from constants import cmd
from server_player import Player
from helpers import game_config

logger = setup_logger('settings.conf', 'server')
ECHO_FREQUENCY = int(game_config.get('OTHER', 'ECHO_FREQUENCY'))
TIMEOUT = int(game_config.get('OTHER', 'TIMEOUT'))


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
        matchingThread = threading.Thread(
            target=self.find_opponent, args=(), daemon=True).start()

        # get connection instances
        while True:
            try:
                # accept connections with ssl socket wrap
                conn, addr = self.socket_ssl.accept()
                logger.info('Connected to: ' +
                            str(addr[0]) + ':' + str(addr[1]))
            except Exception as e:
                logger.error(
                    "Couldn't create secure connection to player, " + str(e))
                raise

            try:
                new_player = Player(conn)
                recvThread = threading.Thread(
                    target=self.player_receive_daemon, args=(new_player,), daemon=True).start()
                connThread = threading.Thread(
                    target=self.player_check_connection, args=(new_player,), daemon=True).start()

                GameServer.players_waitlist.append(new_player)
                GameServer.active_players.append(new_player)
                logger.info('Waiting players: ' +
                            str(len(GameServer.players_waitlist)))
                logger.info('Active online players are: ' +
                            str(len(GameServer.active_players)))
                logger.info('Number of all served players is: ' +
                            str(GameServer.players_count_history))

            except Exception as e:
                logger.error(
                    "Couldn't create a thread, terminating client session. Exception details: " + str(e))
                conn.close()

    def drop_player(self, player):
        """Disconnect a player or end connection with it"""
        logger.warning('Dropping player id: ' + str(player.id))
        player.disconected = True
        if player.is_waiting is False:
            game = self.get_game(player)
            opponent = self.get_opponent(player)
            if opponent is not None:
                # inform opponent then drop it from server lists
                opponent.send(
                    cmd['state'], cmd['state_types']['other_disconnected'])
                if game in self.active_games:
                    self.active_games.remove(game)
                opponent.disconected = True

            self.remove_player('waitlist', player)
            self.remove_player('active', player)

        player.conn.close()

    def remove_players(self, list, player1, player2):
        """remove players of a game from game server lists"""
        if list == 'waitlist':
            if player1 in GameServer.players_waitlist:
                GameServer.players_waitlist.remove(player1)
            if player2 in GameServer.players_waitlist:
                GameServer.players_waitlist.remove(player2)
        elif list == 'active':
            if player1 in GameServer.active_players:
                GameServer.active_players.remove(player1)
            if player2 in GameServer.active_players:
                GameServer.active_players.remove(player2)

    def remove_player(self, list, player):
        """remove a player from the servers lists"""
        if list == 'waitlist':
            if player in GameServer.players_waitlist:
                GameServer.players_waitlist.remove(player)
        elif list == 'active':
            player
            if player in GameServer.active_players:
                GameServer.active_players.remove(player)

    def player_receive_daemon(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info('Running receive thread on player: ' + str(player.id))
        while True:
            if player.disconected:
                break
            player.receive_populate_buffer()
            # time.sleep(1)

    def player_check_connection(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info(
            'Running connection check thread on player: ' + str(player.id))
        counter = 0
        while True:
            if player.disconected:
                break

            if counter % ECHO_FREQUENCY == 0:
                challenge = 'f'
                player.send(cmd['echo'], challenge)
                echo_value = player.receive('echo', 5)

            quit_cmd = player.read_buffer('quit')
            if quit_cmd or player.disconected or echo_value != challenge:
                if quit_cmd:
                    logger.warning(
                        'Player: ' + str(player.id) + ' asked to quit')

                self.drop_player(player)
                break

            time.sleep(1)
            counter += 1

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
                player1.role = "X"
                player2.role = "O"
                player1.opponenet = player2.id
                player2.opponenet = player1.id
                # send the players game info
                player1_send = player1.send_game_info()
                player2_send = player2.send_game_info()
                if player1_send is True and player2_send is True:
                    try:
                        gameThread = threading.Thread(target=self.game_thread, args=(
                            player1, player2), daemon=True).start()
                        player1.is_waiting = False
                        player2.is_waiting = False
                    except Exception as e:
                        logger.error(
                            'could not create game thread, exception message: ' + str(e))

                else:
                    if not player1_send and not player2_send:
                        self.remove_players('waitlist', player1, player2)
                    else:
                        if player1_send is True:
                            self.remove_player('waitlist', player2)
                            player1.send(
                                cmd['state'], cmd['state_types']['other_disconnected'])
                        if player2_send is True:
                            self.remove_player('waitlist', player1)
                            player2.send(
                                cmd['state'], cmd['state_types']['other_disconnected'])

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
        logger.info('Matched player: ' + str(player1.id) +
                    ' with opponenet: ' + str(player1.opponenet))
        self.player1 = player1
        self.player2 = player2
        self.moves_counter = 0
        self.state = ''
        self.board = list('         ')

    def start(self):
        """start the current game"""
        logger.info('Starting the game between: ' +
                    str(self.player1.id) + ' and: ' + str(self.player2.id))
        while True:
            # alternate moves between players
            if self.move(self.player1, self.player2):
                return
            if self.move(self.player2, self.player1):
                return

    def move(self, moving_player, waiting_player):
        """move the players by turn"""
        board_content = "".join(self.board)
        self.send_both_players(cmd['board'], board_content)

        moving_player.send(cmd['state'],
                           cmd['state_types']['your_turn'])
        waiting_player.send(cmd['state'],
                            cmd['state_types']['other_turn'])

        try:
            move = int(moving_player.receive('move', TIMEOUT))
            if move == -1:
                self.send_both_players(cmd['timeout'], '')
                logger.warning("player " + str(moving_player.id) +
                               " has timedout, informing players")
            else:
                if self.board[move - 1] == " ":
                    self.board[move - 1] = moving_player.role
                    self.moves_counter += 1
                else:
                    logger.warning("Player " + str(moving_player.id) +
                                   " wants to take a used position")
        except Exception as e:
            logger.error('Expected an integer move, ' + str(e))
            raise
        # Check if this will result in a win
        if self.moves_counter > 4:
            result, winning_path = self.check_winner(moving_player)
            if (result >= 0):
                self.send_both_players(
                    cmd['board'], ("".join(self.board)))

                if (result == 0):
                    self.send_both_players(
                        cmd['state'], cmd['state_types']['draw'])
                    logger.info('Game between player ' + str(moving_player.id) + ' and '
                                + str(waiting_player.id) + ' ended with a draw.')
                    return True
                if (result == 1):
                    moving_player.send(
                        cmd['state'], cmd['state_types']['win'])
                    waiting_player.send(
                        cmd['state'], cmd['state_types']['lose'])
                    logger.info('Player ' + str(moving_player.id) +
                                ' beated player ' + str(waiting_player.id))
                    return True
                return False

    def send_both_players(self, cmd, msg):
        """send data to both players"""
        self.player1.send(cmd, msg)
        self.player2.send(cmd, msg)

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
