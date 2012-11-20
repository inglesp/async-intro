# curl.py

# This is an illustration of how to make an HTTP request via a socket

import socket, sys, urlparse

def curl(url):
    parsed_url = urlparse.urlsplit(url)
    host = socket.gethostbyname(parsed_url.hostname)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, parsed_url.port or 80))

    sock.send('GET %s HTTP/1.0\r\n' % (parsed_url.path or '/'))
    sock.send('Host: %s\r\n' % parsed_url.hostname)
    sock.send('\r\n')

    response = ''

    while True:
        data = sock.recv(1024)
        if not data:
            sock.close()
            break
        response += data

    print response

if __name__ == '__main__':
    curl(sys.argv[1])
