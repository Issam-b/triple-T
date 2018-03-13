# Import the socket module
import socket
# Import command line arguments
from sys import argv

# setup logging file and format of log statement
import logging
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('client')

# If there are more than 3 arguments
if len(argv) >= 3:
    # Set the address to argument 1, and port number to argument 2
    address = argv[1]
    port_number = argv[2]
else:
    # Ask the user to input the address and port number
    address = input("Please enter the address:")
    port_number = input("Please enter the port:")

# Create the socket object
# 1st parameter: IPv4 networking
# 2nd parameter: socket type, SOCK_STREAM = TCP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# Connection lost
def connection_lost():
    print("Error: connection_lost")
    try:
        # Inform Server, send "q"
        client_socket.send("q".encode())
    except:
        raise


# Receive msg
def client_receive(size, expected_command):
    try:
        msg = client_socket.recv(size).decode()

        if msg[0] == "q":
            print(msg[1:])
            connection_lost()
        # If the message is not the expected type
        elif msg[0] != expected_command:
            connection_lost()
        # If received an integer from the client
        elif msg[0] == "m":
            return int(msg[1:])
        else:
            return msg[1:]
        return msg
    except:
        raise
    return None


# Send Msg
# cmd = command convention, msg = sent msg
def client_send(cmd, msg):
    try:
        client_socket.send((cmd + msg).encode())

    except Exception as e:
        print("Error client_send")
        logger.error(str(e))


# Connecting to Server
while True:
    try:
        print("Trying to Connect Server...")
        # Connect to host address, port
        client_socket.connect((address, int(port_number)))
        print("Connected to Server")
        # Send m test
        client_send('m', "1")
        # Error, break loop
        break

    except Exception as e:
        print("Error Connecting")
        logger.error(str(e))

# Print Welcome msg from Server
print(client_socket.recv(1024).decode())

while True:
    print("Game Stuff")

# Shut down the socket (prevent more send/rec)
client_socket.shutdown(socket.SHUT_RDWR)
# Close Socket
client_socket.close()
