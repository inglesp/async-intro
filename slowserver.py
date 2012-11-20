# slowserver.py

import sys
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.protocols.policies import ProtocolWrapper, WrappingFactory
from twisted.web.static import File
from twisted.web.server import Site

class SlowProtocol(ProtocolWrapper):
    def __init__(self, *args, **kwargs):
        ProtocolWrapper.__init__(self, *args, **kwargs)
        self.writesOutstanding = False
        self.loseConnectionWhenReady = False
        self.writeLimit = None
        self.buf = ''

    def setWriteLimit(self, limit):
        self.writeLimit = limit

    def write(self, data):
        self.buf += data
        if not self.writesOutstanding:
            self.actuallyWrite()

    def actuallyWrite(self):
        if self.writeLimit is None:
            data = self.buf
            self.buf = ''
        else:
            data = self.buf[:self.writeLimit]
            self.buf = self.buf[self.writeLimit:]

        ProtocolWrapper.write(self, data)

        if data != '':
            self.writesOutstanding = True
            reactor.callLater(1, self.actuallyWrite)
        else:
            self.writesOutstanding = False
            if self.loseConnectionWhenReady:
                self.actuallyLoseConnection()

    def loseConnection(self):
        self.loseConnectionWhenReady = True
        if not self.writesOutstanding:
            self.actuallyLoseConnection()

    def actuallyLoseConnection(self):
        ProtocolWrapper.loseConnection(self)

class SlowFactory(WrappingFactory):
    protocol = SlowProtocol

    def __init__(self, wrappedFactory, writeLimit):
        WrappingFactory.__init__(self, wrappedFactory)
        self.writeLimit = writeLimit

    def buildProtocol(self, addr):
        protocol = WrappingFactory.buildProtocol(self, addr)
        protocol.setWriteLimit(self.writeLimit)
        return protocol

if __name__ == '__main__':
    resource = File(sys.argv[1])
    factory = Site(resource)
    endpoint = TCP4ServerEndpoint(reactor, 8080)
    endpoint.listen(SlowFactory(factory, 2048))
    reactor.run()
