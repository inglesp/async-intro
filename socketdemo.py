# socketdemo.py

# Import the socket module
import socket

# Create a socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Make a connection to a remote host -- in this case it's localhost
sock.connect(('127.0.0.1', 1234))

# Send some data to the remote host
sock.send('Hello world')

# Receive at most 1024 bytes sent by the remote host -- note that this blocks
data = sock.recv(1024)
print data

# Close the socket
sock.close()
