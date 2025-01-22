from abc import ABC, abstractmethod

from fw_fanctrl.exception.UnimplementedException import UnimplementedException


class SocketController(ABC):
    @abstractmethod
    def startServerSocket(self, commandCallback=None):
        raise UnimplementedException()

    @abstractmethod
    def stopServerSocket(self):
        raise UnimplementedException()

    @abstractmethod
    def isServerSocketRunning(self):
        raise UnimplementedException()

    @abstractmethod
    def sendViaClientSocket(self, command):
        raise UnimplementedException()
