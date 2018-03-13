#! /usr/bin/python3

# Import the socket module
import socket
# Import command line arguments
from sys import argv
from configparser import ConfigParser
import time

# setup logging file and format of log statement
import logging
import logging.config

logging.config.fileConfig('settings.conf')
logger = logging.getLogger('client')

# Create the socket object
# 1st parameter: IPv4 networking
# 2nd parameter: socket type, SOCK_STREAM = TCP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# Connection lost
def connection_lost():
    print("Error: connection_lost")
    # try:
    #     # Inform Server, send "q"
    #     # client_socket.send("q".encode())
    # except:
    #     raise


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
        print('sending: ' + str(cmd + msg))
        client_socket.send((cmd + msg).encode())

    except Exception as e:
        print("Error client_send")
        logger.error(str(e))

def client_connect():
  # get configuration
  config = ConfigParser()
  config.read('settings.conf')
  address = config.get('connection', 'address')
  port = config.get('connection', 'port')

  print("Trying to Connect Server...")
  # Connect to host address, port
  client_socket.connect((address, int(port)))
  print("Connected to Server")


while True:
  try:
    # connect to server
    client_connect()
    break

  except Exception as e:
    logger.error('Error connectiog, exception message: ' + str(e))
  finally:
    time.sleep(1)

# Connecting to Server
while True:
  # Send e test
  # msg = client_receive(2, 'e')
  # print(str(msg[0:1]))
  # if msg[0:1] == 'f':
  #   client_send('e', "f")
  # wait for match
  msg = client_receive(2,'g')
  print('player role is: ' + str(msg))
  client_send('c', '1')
    # Send e test
  msg = client_receive(2, 'e')
  print(str(msg[0:1]))
  if msg[0:1] == 'f':
    client_send('e', "f")

  time.sleep(1)

# Print Welcome msg from Server
print(client_socket.recv(1024).decode())

# while True:
#     print("Game Stuff")


def convert_empty_board_position(s):
 new_s = list("123456789")
 for i in range(0, 8):
  if(s[i] != " "):
   new_s[i] = s[i]
 return "".join(new_s)


def format_board(s):
 if(len(s) != 9):
  print("Error: there should be 9 symbols")
  return ""

 # Draw the grid board
# print("|1|2|3|");
# print("|4|5|6|");
# print("|7|8|9|");
 return "|" + s[0] + "|" + s[1] + "|" + s[2] + "|\n" + "|" + s[3] + "|" + s[4] + "|" + s[5] + "|\n" + "|" + s[6] + "|" + s[7] + "|" + s[8] + "|\n"


while True:
 board_content = client_socket.recv(9).decode()
 print("Board Content" + format_board(board_content))

 command = client_socket.recv(1).decode()

 # If it's this player's turn to move
 if(command == "Y"):
		# Print out the current board with " " converted to the position number
		print("Current board:\n" + format_board(convert_empty_board_position(board_content)))
 else:
		# Print out the current board
		print("Current board:\n" + format_board(board_content))

 if(command == "Y"):
  while True:
   position = int(input("please enter the postion (1~9): "))
   if (position >= 1 and position <= 9):
    if (board_content[position-1] != " "):
     print("That postion is already taken. Please choose another")
    else:
     break
   else:
    print("enter a value between 1 to 9")
  client_socket.send(str(position).encode())

 elif (command == "N"):
  print("current board:\n"+format_board(board_content))
  print("Waiting for the other player to make a move")

 elif (command == "D"):
  print("It's a draw.")
  break

 elif (command == "W"):
  print("You WIN!")
  break

 elif (command == "L"):
  print("You lose.")
  break

# Shut down the socket (prevent more send/rec)
client_socket.shutdown(socket.SHUT_RDWR)
# Close Socket
client_socket.close()
