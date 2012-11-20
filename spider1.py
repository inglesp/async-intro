# spider1.py

# This is a simple implementation of a single-threaded, blocking web crawler.
# A Spider object makes requests for urls one at a time.  It is effective, but
# spends most of its time waiting on responses from the web server.

# We'll see approaches for speeding this process up by making requests in
# parallel with threads (spider2.py) and via asynchronous I/O (spider3.py,
# spider4.py).

import re
import socket
import sys
import urlparse

from bs4 import BeautifulSoup

class Spider(object):
    def __init__(self, root_url):
        netloc, path = parse_url(root_url)
        self.netloc = netloc

        # Maps urls to the status code returned when requesting that url
        self.results = {}

        # A list of urls that we have seen but have not yet requested
        self.outstanding = [root_url]

    def run(self):
        while self.outstanding:
            url = self.outstanding.pop()
            self.maybe_make_request(url)

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
            response = self.get_response(sock)
            self.handle_response(url, response)
        except socket.error as e:
            print 'error:', e
            return None

    def make_connection(self, netloc):
        hostname, port = parse_netloc(netloc)
        host = socket.gethostbyname(hostname)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        return sock

    def send_request(self, sock, hostname, path):
        sock.send('GET %s HTTP/1.0\r\n' % path.encode('utf-8'))
        sock.send('Host: %s\r\n' % hostname)
        sock.send('\r\n')

    def get_response(self, sock):
        response = ''

        while True:
            data = sock.recv(1024)
            if not data:
                # Zero bytes received
                sock.close()
                break
            else:
                response += data

        return response

    def handle_response(self, url, response):
        print 'got response for', url
        response = self.parse_response(response)
        self.results[url] = response['status_code']
        try:
            method = getattr(self, 'handle_%s' % response['status_code'])
        except AttributeError:
            pass
        else:
            method(url, response)

    def parse_response(self, response):
        status_plus_headers, text = response.split('\r\n\r\n', 1)
        lines = status_plus_headers.split('\r\n')

        status_code = re.match('HTTP/1.[01] (\d{3})', lines[0]).groups()[0]

        headers = {}

        for line in lines[1:]:
            key, val = line.split(':', 1)
            headers[key.strip()] = val.strip()

        return {'status_code': status_code,
                'headers': headers,
                'text': text}

    def handle_200(self, url, response):
        netloc, _ = parse_url(url)
        if netloc == self.netloc and \
                response['headers']['Content-Type'] == 'text/html':
            # This is a response to a request for a url on the same host as the
            # original request, and the response is a web page
            soup = BeautifulSoup(response['text'])
            for link in soup.find_all('a'):
                # Make requests for all urls linked to in page body
                self.outstanding.append(link.get('href'))

    def handle_301(self, url, response):
        # Make request for location of permanently-moved resource
        self.outstanding.append(response['headers']['Location'])

    def handle_302(self, url, response):
        # Make request for location of temporarily-moved resource
        self.outstanding.append(response['headers']['Location'])

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
