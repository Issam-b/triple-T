#! /usr/bin/python3

# socket module
import socket
# argv from sys module to get arguments
from sys import argv
# logging module to log events to file
import logging

class Server:
    """Server class to handle connection related calls."""

    def __init__(self):
        """Initializes the server object with a server socket."""
		# create the TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def bind_server(self, host, port):
        """bind and listen to the the given port."""
        
        self.port = port

        while True:
            # try to bind
            try:
                self.server_socket.bind((host, self.port))
                print_with_log("Bind successful to port " + str(self.port), 'info')
                self.server_socket.listen(5)
                print_with_log("Listening on port " + str(self.port), 'info')
                break

            except socket.error as e:
                # print errors
                print_with_log(str(e), 'error')
                
                # show menu
                option = input('Choose an option:\n[N]ew port | [Q]uit : ')
                
                # assign new port or exit
                if(option.lower()) == 'n':
                    self.port = input('Enter new port number: ')
                    print_with_log("New port specified: " + str(self.port), 'info')
                    print('\n')
                elif(option.lower()) == 'q':
                    print_with_log("Exit the program!", 'info')
                    exit(0)
                else:
                    print_with_log("Bad choice, exit!", 'error')
                    exit(-1)


    def show_connection(self):
        """show connected clients."""
        # get connection instance
        self.conn, self.addr = self.server_socket.accept()
        print('Connected to: ' + str(self.addr[0]) + ':' + str(self.addr[1]))

    def close(self):
        # TODO: add log
        self.server_socket.close()
            
class GameServer(Server):
    """Handle game start and clients management."""

    def __init__(self):
        """Get the socket connection object from Server class."""
        Server.__init__(self)
    
    # TODO: add clients connection logic, and players matching and game itself


def print_with_log(message, log_type):
    """Helper function to print and log events at the same time"""
    print(message)
    if(log_type == 'info'):
        logging.info(message)
    elif(log_type == 'error'):
        logging.error(message)
    elif(log_type == 'debug'):
        logging.debug(message)


def main():
    # setup logging file and format of log statement
    logging.basicConfig(filename="server.log", level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # If there are more than 2 arguments 
    if(len(argv) >= 2):
        # Set port number to argument 1
        port = argv[1]
    else:
        # get the port number to bind to
        port = input('Enter the port number: ')

    try:
        server = GameServer()
        # bind to port number as integer
        server.bind_server('', int(port))
        # show connected clients
        server.show_connection()
        # close the socket connection before terminating the server
        server.close()

        print_with_log("Exiting", 'info')
        exit(-1)

    except Exception as e:
        print_with_log(str(e), 'error')

    
if __name__ == __name__:
    main()