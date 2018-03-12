# Import the socket module
import socket
# Import command line arguments
from sys import argv

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

# Connecting to Server
while True:
    try:
        print("Trying to Connect Server...")
        # Connect to host address, port
        client_socket.connect((address, int(port_number)))
        # Error, break loop
        break

    except:
        # Caught an error
        print("Error in Connecting!")

# Print Welcome Message from Server
print(client_socket.recv(1024).decode())

# Shut down the socket (prevent more send/rec)
client_socket.shutdown(socket.SHUT_RDWR)
# Close Socket
client_socket.close()
