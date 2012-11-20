# echoserver.py

import sys
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ServerEndpoint


class Echo(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

if __name__ == '__main__':
    port = int(sys.argv[1])
    endpoint = TCP4ServerEndpoint(reactor, port)
    factory = Factory()
    factory.protocol = Echo
    endpoint.listen(factory)
    reactor.run()
