# spider3.py

# This is a first attempt at an implementation of a single-threaded, non-
# blocking web crawler.  A single Spider object makes many HTTP requests, any
# number of which may be outstanding at any one time.  The Spider makes
# requests via non-blocking sockets, and then loops over all sockets with
# outstanding requests, reading from each as data arrives.

# Note that the event loop is tangled up with the rest of the code.  In
# spider4.py, we'll see how to separate the event loop.

import errno
import re
import socket
import sys
import urlparse

from bs4 import BeautifulSoup

class Spider(object):
    def __init__(self, root_url):
        self.root_url = root_url
        netloc, path = parse_url(root_url)
        self.netloc = netloc

        # Maps urls to the status code returned when requesting that url
        self.results = {}

        # Maps sockets with outstanding requests to a tuple:
        #   (url of request, data received on socket so far)
        self.sockets = {}

    def run(self):
        # Make first request
        self.maybe_make_request(self.root_url)

        while self.sockets:
            # List of sockets which have received all their data
            complete = []

            # Loop over sockets with outstanding requests, attempting to read
            # data from each in turn -- note this is inefficient: use the
            # select module instead
            for sock in self.sockets:
                while True:
                    try:
                        data = sock.recv(1024)
                    except socket.error as e:
                        if e.args[0] == errno.EWOULDBLOCK:
                            # There's no data to be read
                            break
                        else:
                            # Something else has gone wrong
                            raise

                    if not data:
                        # Zero bytes received
                        sock.close()
                        complete.append(sock)
                        break
                    else:
                        # Update record of data received on this socket
                        url, response = self.sockets[sock]
                        self.sockets[sock] = url, response + data

            for sock in complete:
                # All data now received on this socket
                self.handle_response(sock)

        # All requests are complete
        print self.results

    def maybe_make_request(self, url):
        url = self.normalise(url)
        if url is None or url in self.results:
            # Either the url was a fragment, or we've already requested it
            return

        self.make_request(url)

    def make_request(self, url):
        print 'requesting', url
        self.results[url] = None

        try:
            netloc, path = parse_url(url)
            sock = self.make_connection(netloc)
            self.send_request(sock, netloc, path)

            # Rather than wait for a response, add to list (actually a dict) of
            # sockets that are checked by run() for data
            self.sockets[sock] = url, ''

        except socket.error as e:
            print 'error:', e
            return None

    def make_connection(self, netloc):
        hostname, port = parse_netloc(netloc)
        host = socket.gethostbyname(hostname)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

        # Put the socket in non-blocking mode
        sock.setblocking(0)
        return sock

    def send_request(self, sock, hostname, path):
        sock.send('GET %s HTTP/1.0\r\n' % path.encode('utf-8'))
        sock.send('Host: %s\r\n' % hostname)
        sock.send('\r\n')

    def handle_response(self, sock):
        # Retrieve the url and response corresponding to the socket
        url, response = self.sockets[sock]

        # Remove socket from list of sockets with outstanding responses
        del self.sockets[sock]

        print 'got response for', url

        # Parse the response, and record the status code
        response = self.parse_response(response)
        self.results[url] = response['status_code']

        # If we know how to handle a response with this status code, do so now
        try:
            method = getattr(self, 'handle_%s' % response['status_code'])
        except AttributeError:
            pass
        else:
            method(url, response)

    def parse_response(self, response):
        status_plus_headers, body = response.split('\r\n\r\n', 1)
        lines = status_plus_headers.split('\r\n')

        status_code = re.match('HTTP/1.[01] (\d{3})', lines[0]).groups()[0]

        headers = {}

        for line in lines[1:]:
            key, val = line.split(':', 1)
            headers[key.strip()] = val.strip()

        return {'status_code': status_code,
                'headers': headers,
                'body': body}

    def handle_200(self, url, response):
        netloc, _ = parse_url(url)
        if netloc == self.netloc and \
                response['headers']['Content-Type'] == 'text/html':
            # This is a response to a request for a url on the same host as the
            # original request, and the response is a web page
            soup = BeautifulSoup(response['body'])
            for link in soup.find_all('a'):
                # Make requests for all urls linked to in page body
                self.maybe_make_request(link.get('href'))

    def handle_301(self, url, response):
        # Make request for location of permanently-moved resource
        self.maybe_make_request(response['headers']['Location'])

    def handle_302(self, url, response):
        # Make request for location of temporarily-moved resource
        self.maybe_make_request(response['headers']['Location'])

    def normalise(self, url):
        netloc, path = parse_url(url)
        if not netloc and not path:
            # url was a fragment
            return None
        return 'http://' + (netloc or self.netloc) + path

def parse_url(url):
    parsed_url = urlparse.urlsplit(url)
    if parsed_url.port:
        netloc = '%s:%s' % (parsed_url.hostname, parsed_url.port)
    else:
        netloc = parsed_url.hostname
    if parsed_url.path.startswith('/'):
        path = parsed_url.path
    else:
        path = '/' + parsed_url.path
    return netloc, path

def parse_netloc(netloc):
    if ':' in netloc:
        hostname, port = netloc.split(':')
        return hostname, int(port)
    else:
        return netloc, 80

if __name__ == '__main__':
    spider = Spider(sys.argv[1])
    spider.run()
