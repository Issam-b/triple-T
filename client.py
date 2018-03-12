#! /usr/bin/python3

import socket 
from sys import argv 

class Client:

  def __init__(self):
    ''' Initializtion for client '''
    self.client_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

  def connect(self, address, port_number):
    ''' tries to connect and returns True when connection occurs '''
    while True:
      try:
        print("Connecting to the game server")
        self.client_socket.timeout(10)
        self.client_socket.connect((address,int(port_number)))
        return True
      except:
        print("Received an error while attempting to connect to " + str(address) + " from port number " + int(port_number))
        self.__connect_failed__()
    return False

  def __connect_failed__(self):
    pass