#! /usr/bin/python3

import threading
import time
import sys
from helpers import setup_logger
from helpers import game_config
from helpers import cmd
from server import Server
from server_player import Player
import socket
import ssl


logger = setup_logger("settings.conf", "server")
ECHO_FREQUENCY = int(game_config.get("OTHER", "ECHO_FREQUENCY"))
TIMEOUT = int(game_config.get("OTHER", "TIMEOUT"))
echo_enable = game_config.get("OTHER", "echo")
server2_address = game_config.get("connection", "address2")
server2_port = game_config.get("connection", "port2")
DEBUG = True if game_config.get("DEBUG", "DEBUG") == "True" else False
message_length = int(game_config.get("OTHER", "message_length"))
CERT = game_config.get("SSL", "CERT")


class GameServer(Server):
    """Handle game start and clients management."""
    run_once = False
    players_waitlist = []
    active_players = []
    all_players_count = 0
    active_games = []

    def __init__(self, host, port):
        """Get the socket connection object from Server class."""
        self.host = host
        self.port = port
        Server.__init__(self)

    def start(self):
        """Start the game server."""
        self.__receive_connections()

    def __receive_connections(self):
        """show connected clients."""
        running_server_exist, running_server_conn = self.connect_to_running_server(
            server2_address, server2_port)
        if running_server_exist:
            self.echo_running_server(running_server_conn)
            logger.error("Running server is down, taking over!")

        self.bind_server(self.host, int(self.port))

        threading.Thread(
            target=self.match_players_thread, args=(), daemon=True).start()
        while True:
            conn, conn_type = self.accept_new_player()
            if conn_type == "server":
                self.create_backup_server_thread(conn)
            else:
                self.create_player_connection_threads(conn)

    def connect_to_running_server(self, address, port):
        try:
            logger.info("Trying to connect and find active servers")
            m_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ssl_socket = ssl.wrap_socket(
                m_socket, cert_reqs=ssl.CERT_REQUIRED, ca_certs=CERT)
            ssl_socket.connect((address, int(port)))
            logger.info("Connected to a running server")

            return True, ssl_socket
        except Exception:
            logger.warning("No other running server")
            return False, ""

    def create_backup_server_thread(self, conn):
        logger.info("Backup server is up")
        try:
            threading.Thread(
                target=self.backup_server_echo_response_thread, args=(conn,), daemon=True).start()
        except Exception as e:
            logger.error(
                "Couldn't create a thread, terminating backup server session,  " + str(e))
            self.close_socket(conn)

    def backup_server_echo_response_thread(self, backup_server_conn):
        logger.info("Start backup server echo thread")
        while True:
            msg = self.server_receive_echo(backup_server_conn, "backup")
            if msg is not None:
                send_sussess = self.server_send_echo(
                    backup_server_conn, msg, "backup")
                if not send_sussess:
                    break
            else:
                break

    def echo_running_server(self, running_server):
        while True:
            challenge = "f"
            self.server_send_echo(running_server, challenge, "running")
            response = self.server_receive_echo(running_server, "running")
            if response != challenge:
                logger.error("Lost connection to running server")
                break
            time.sleep(ECHO_FREQUENCY)

    def server_send_echo(self, conn, msg, server_type):
        try:
            conn.send((cmd["echo"] + msg).encode())
            if DEBUG:
                logger.info("sending echo " + str(msg) + " to backup server")
            return True
        except Exception:
            logger.error("Send failed to " + str(server_type) + " server")
            logger.error("Lost connection to " + str(server_type) + " server")
            return False

    def server_receive_echo(self, conn, server_type):
        try:
            msg = conn.recv(message_length).decode()
            if DEBUG:
                logger.info("received: " + str(msg) +
                            " from backup server")
            if len(msg) > 0:
                return msg[1]
            else:
                return ""
        except Exception:
            logger.error("Failed while receiving msg from " +
                         str(server_type) + " server")

    def create_player_connection_threads(self, conn):
        try:
            new_player = Player(conn)
            threading.Thread(
                target=self.player_receive_thread, args=(new_player,), daemon=True).start()
            threading.Thread(
                target=self.player_check_connection_thread, args=(new_player,), daemon=True).start()

            GameServer.players_waitlist.append(new_player)
            GameServer.active_players.append(new_player)
            self.log_players_stats()

        except Exception as e:
            logger.error(
                "Couldn't create a thread, terminating client session,  " + str(e))
            self.close_socket(conn)

    def accept_new_player(self):
        conn_type = ""
        conn = ""
        try:
            # accept connections with ssl socket wrap
            conn, addr = self.socket_ssl.accept()
            # TODO remove run_once variable
            if addr[0] == server2_address and not GameServer.run_once:
                conn_type = "server"
                GameServer.run_once = True
            else:
                conn_type = "client"
            logger.info("Connected to: " +
                        str(addr[0]) + ":" + str(addr[1]))

        except Exception as e:
            logger.error(
                "Couldn't create secure connection to player, " + str(e))
        return conn, conn_type

    def log_players_stats(self):
        logger.info("Waiting players: " +
                    str(len(GameServer.players_waitlist)))
        logger.info("Active online players are: " +
                    str(len(GameServer.active_players)))
        logger.info("Number of all served players is: " +
                    str(GameServer.all_players_count))

    def drop_player(self, player):
        """Disconnect a player or end connection with it"""
        if player.dropped:
            return
        logger.warning("Dropping player id: " + str(player.id))
        player.disconected = True
        if not player.is_waiting:
            game = self.get_game(player)
            if game in self.active_games:
                self.active_games.remove(game)
            opponent = self.get_opponent(player)
            if opponent is not None:
                opponent.disconected = True
                # self.announce_player_disconnected([opponent, ])

        self.remove_player("waitlist", player)
        self.remove_player("active", player)
        self.announce_player_disconnected([player, ])

        self.close_socket(player.conn)
        player.dropped = True

    def remove_players(self, list, player1, player2):
        """remove players of a game from game server lists"""
        if list == "waitlist":
            if player1 in GameServer.players_waitlist:
                GameServer.players_waitlist.remove(player1)
            if player2 in GameServer.players_waitlist:
                GameServer.players_waitlist.remove(player2)
        elif list == "active":
            if player1 in GameServer.active_players:
                GameServer.active_players.remove(player1)
            if player2 in GameServer.active_players:
                GameServer.active_players.remove(player2)
        # self.announce_player_disconnected([player1, player2])

    def remove_player(self, list, player):
        """remove a player from the servers lists"""
        if list == "waitlist":
            if player in GameServer.players_waitlist:
                GameServer.players_waitlist.remove(player)
        elif list == "active":
            player
            if player in GameServer.active_players:
                GameServer.active_players.remove(player)

    def player_receive_thread(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info("Start receive thread of player " + str(player.id))
        errors_counter = 0
        while True:
            is_success = player.receive_populate_buffer()
            if not is_success:
                errors_counter += 1
                time.sleep(1)
            if errors_counter == 2 or player.disconected:
                # self.announce_player_disconnected([player, ])
                self.drop_player(player)
                break

    def announce_player_disconnected(self, player_list):
        for player in player_list:
            player.send(cmd["state"], cmd["state_types"]["other_disconnected"])

    def player_check_connection_thread(self, player):
        """create a thread for the player and check his connection periodically"""
        logger.info("Start connection check thread of player " + str(player.id))
        counter = 0
        while True:
            if echo_enable == "1":
                if counter % ECHO_FREQUENCY == 0:
                    echo_value, challenge = self.check_echo_response(player)
            else:
                echo_value, challenge = ("f", "f")

            quit_cmd = player.read_buffer("quit")
            if quit_cmd or player.disconected or echo_value != challenge:
                if quit_cmd:
                    logger.warning(
                        "Player: " + str(player.id) + " asked to quit")
                self.drop_player(player)
                break

            counter += 1
            time.sleep(1)

    def check_echo_response(self, player):
        challenge = "f"
        player.send(cmd["echo"], challenge)
        echo_value = player.receive_with_wait("echo", 10)
        return echo_value, challenge

    def match_players_thread(self):
        """find an opponenet for the player"""
        logger.info("Start players matching thread")
        while True:
            if len(self.players_waitlist) > 1:
                player1, player2 = self.assign_roles()

                player1_send, player2_send = self.send_roles(
                    player1, player2)
                if player1_send is True and player2_send is True:
                    try:
                        threading.Thread(target=self.game_thread, args=(
                            player1, player2), daemon=True).start()
                        player1.is_waiting = False
                        player2.is_waiting = False
                    except Exception as e:
                        logger.error(
                            "could not create game thread, " + str(e))
                else:
                    self.create_game_fail_remove_players(
                        player1_send, player2_send, player1, player2)

            time.sleep(1)

    def send_roles(self, player1, player2):
        player1_send = player1.send_game_info()
        player2_send = player2.send_game_info()
        return player1_send, player2_send

    def assign_roles(self):
        logger.info("Matching players from waitlist")
        player1 = GameServer.players_waitlist[0]
        player2 = GameServer.players_waitlist[1]
        player1.match = player2
        player2.match = player1
        player1.role = "X"
        player2.role = "O"
        player1.opponenet = player2.id
        player2.opponenet = player1.id
        return player1, player2

    def create_game_fail_remove_players(self, player1_send, player2_send, player1, player2):
        if not player1_send and not player2_send:
            self.remove_players("waitlist", player1, player2)
        else:
            if player1_send is True:
                self.remove_player("waitlist", player2)
                self.announce_player_disconnected([player1, ])
            if player2_send is True:
                self.remove_player("waitlist", player1)
                self.announce_player_disconnected([player2, ])

    def get_opponent(self, player):
        """return opponnet player object of a player"""
        for pl in GameServer.active_players:
            if pl.id == player.opponenet:
                return pl

    def get_game(self, player):
        """return an object game related to a player"""
        for game in self.active_games:
            if player in {game.player1, game.player2}:
                return game
            else:
                return None

    def game_thread(self, player1, player2):
        """start a new game in seperate thread"""
        logger.info("Start new game thread")
        try:
            new_game = Game(player1, player2)
            self.active_games.append(new_game)
            new_game.start()
        except Exception:
            logger.error("Game ended unexpectedly")
            self.announce_player_disconnected([player1, player2])

    def close_socket(self, conn):
        try:
            conn.close()
        except Exception:
            logger.error("Couldn't close socket")


class Game:
    """The game logic, moves, win and lose events handler"""

    def __init__(self, player1, player2):
        """initiate the game"""
        logger.info("Matched player: " + str(player1.id) +
                    " with opponenet: " + str(player1.opponenet))
        self.player1 = player1
        self.player2 = player2
        self.moves_counter = 0
        self.state = ""
        self.board = list("         ")

    def start(self):
        """start the current game"""
        logger.info("Starting the game between: " +
                    str(self.player1.id) + " and: " + str(self.player2.id))
        while True:
            # alternate moves between players
            if self.move(self.player1, self.player2):
                return
            if self.move(self.player2, self.player1):
                return

    def move(self, moving_player, waiting_player):
        """move the players by turn"""
        self.announce_board_content()
        self.announce_turns(moving_player, waiting_player)
        if not self.receive_move(moving_player):
            logger.warning("Game has ended")
            return True
        if self.moves_counter > 4:
            self.check_game_result(moving_player, waiting_player)

    def receive_move(self, moving_player):
        try:
            move_str = moving_player.receive_with_wait("move", TIMEOUT)
            if self.is_int(move_str):
                move = int(move_str)
                if move == -1:
                    self.send_both_players(cmd["timeout"], "")
                    logger.warning("player " + str(moving_player.id) +
                                   " has timedout, informing players")
                else:
                    self.update_board(move, moving_player)
                return True
            else:
                return False
        except Exception:
            logger.error("Didn't get an integer move")
            return False

    def announce_board_content(self):
        board_content = "".join(self.board)
        self.send_both_players(cmd["board"], board_content)

    def check_game_result(self, moving_player, waiting_player):
        result, winning_path = self.check_win_path(moving_player)
        if (result >= 0):
            self.send_both_players(
                cmd["board"], ("".join(self.board)))

            if (result == 0):
                self.announce_draw(moving_player, waiting_player)
                return True
            elif (result == 1):
                self.announce_win_lose(moving_player, waiting_player)
                return True
        return False

    def update_board(self, move, moving_player):
        if self.board[move - 1] == " ":
            self.board[move - 1] = moving_player.role
            self.moves_counter += 1
        else:
            logger.warning("Player " + str(moving_player.id) +
                           " wants to take a used position")

    def announce_turns(self, moving_player, waiting_player):
        moving_player.send(cmd["state"],
                           cmd["state_types"]["your_turn"])
        waiting_player.send(cmd["state"],
                            cmd["state_types"]["other_turn"])

    def announce_draw(self, moving_player, waiting_player):
        self.send_both_players(
            cmd["state"], cmd["state_types"]["draw"])
        logger.info("Game between player " + str(moving_player.id) + " and "
                    + str(waiting_player.id) + " ended with a draw.")

    def announce_win_lose(self, moving_player, waiting_player):
        moving_player.send(
            cmd["state"], cmd["state_types"]["win"])
        waiting_player.send(
            cmd["state"], cmd["state_types"]["lose"])
        logger.info("Player " + str(moving_player.id) +
                    " beated player " + str(waiting_player.id))

    def is_int(self, digit):
        try:
            int(digit)
            return True
        except ValueError:
            return False

    def send_both_players(self, cmd, msg):
        """send data to both players"""
        self.player1.send(cmd, msg)
        self.player2.send(cmd, msg)

    def check_win_path(self, player):
        """Checks if the player wins the game. Returns 1 if wins,
        0 if it"s a draw, -1 if there"s no result yet."""
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

        # If there"s no empty position left, draw
        if " " not in s:
            return 0, ""

        # The result cannot be determined yet
        return -1, ""
