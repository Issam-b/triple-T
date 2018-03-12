#! /usr/bin/python3

# socket module
import socket
# argv from sys module to get arguments
from sys import argv
# logging module to log events to file
import logging
import logging.config

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
        
        self.port = port

        while True:
            # try to bind
            try:
                self.server_socket.bind((host, int(self.port)))
                logger.info('Bind successful to port ' + str(self.port))
                self.server_socket.listen(5)
                logger.info('Listening on port ' + str(self.port))
                break

            except socket.error as e:
                # print errors
                logger.error(str(e))
                
                # show menu
                option = input('Choose an option:\n[N]ew port | [Q]uit : ')
                
                # assign new port or exit
                if(option.lower()) == 'n':
                    self.port = input('Enter new port number: ')
                    logger.info('New port specified: ' + str(self.port))
                    print('\n')
                elif(option.lower()) == 'q':
                    logger.info('Exit the program!')
                    exit(0)
                else:
                    logger.error('Bad choice, exit!')
                    exit(-1)


    def show_connection(self):
        """show connected clients."""
        # get connection instance
        self.conn, self.addr = self.server_socket.accept()
        logger.info('Connected to: ' + str(self.addr[0]) + ':' + str(self.addr[1]))

    def close(self):
        logger.info('Closing socket')
        self.server_socket.close()
            
class GameServer(Server):
    """Handle game start and clients management."""

    def __init__(self):
        """Get the socket connection object from Server class."""
        Server.__init__(self)
    
    # TODO: add clients connection logic, and players matching and game itself


def main():
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

        logger.info('Exiting')
        exit(-1)

    except Exception as e:
        logger.error(str(e))

    
if __name__ == __name__:
    main()