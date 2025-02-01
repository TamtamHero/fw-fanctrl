from abc import ABC, abstractmethod

from fw_fanctrl.exception.UnimplementedException import UnimplementedException


class SocketController(ABC):
    @abstractmethod
    def start_server_socket(self, command_callback=None):
        raise UnimplementedException()

    @abstractmethod
    def stop_server_socket(self):
        raise UnimplementedException()

    @abstractmethod
    def is_server_socket_running(self):
        raise UnimplementedException()

    @abstractmethod
    def send_via_client_socket(self, command):
        raise UnimplementedException()
