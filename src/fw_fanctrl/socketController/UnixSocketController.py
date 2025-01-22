import io
import os
import shlex
import socket
import sys
from abc import ABC

from src import COMMANDS_SOCKET_FILE_PATH, SOCKETS_FOLDER_PATH
from .CommandParser import CommandParser
from .exception.SocketAlreadyRunningException import SocketAlreadyRunningException
from .socketController.SocketController import SocketController


class UnixSocketController(SocketController, ABC):
    server_socket = None

    def startServerSocket(self, commandCallback=None):
        if self.server_socket:
            raise SocketAlreadyRunningException(self.server_socket)
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(COMMANDS_SOCKET_FILE_PATH):
            os.remove(COMMANDS_SOCKET_FILE_PATH)
        try:
            if not os.path.exists(SOCKETS_FOLDER_PATH):
                os.makedirs(SOCKETS_FOLDER_PATH)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(COMMANDS_SOCKET_FILE_PATH)
            os.chmod(COMMANDS_SOCKET_FILE_PATH, 0o777)
            self.server_socket.listen(1)
            while True:
                client_socket, _ = self.server_socket.accept()
                parsePrintCapture = io.StringIO()
                try:
                    # Receive data from the client
                    data = client_socket.recv(4096).decode()
                    original_stderr = sys.stderr
                    original_stdout = sys.stdout
                    # capture parsing std outputs for the client
                    sys.stderr = parsePrintCapture
                    sys.stdout = parsePrintCapture
                    try:
                        args = CommandParser(True).parseArgs(shlex.split(data))
                    finally:
                        sys.stderr = original_stderr
                        sys.stdout = original_stdout
                    commandReturn = commandCallback(args)
                    if not commandReturn:
                        commandReturn = "Success!"
                    if parsePrintCapture.getvalue().strip():
                        commandReturn = parsePrintCapture.getvalue() + commandReturn
                    client_socket.sendall(commandReturn.encode("utf-8"))
                except SystemExit:
                    client_socket.sendall(f"{parsePrintCapture.getvalue()}".encode("utf-8"))
                except Exception as e:
                    print(
                        f"[Error] > An error occurred while treating a socket command: {e}",
                        file=sys.stderr,
                    )
                    client_socket.sendall(f"[Error] > An error occurred: {e}".encode("utf-8"))
                finally:
                    client_socket.shutdown(socket.SHUT_WR)
                    client_socket.close()
        finally:
            self.stopServerSocket()

    def stopServerSocket(self):
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

    def isServerSocketRunning(self):
        return self.server_socket is not None

    def sendViaClientSocket(self, command):
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client_socket.connect(COMMANDS_SOCKET_FILE_PATH)
            client_socket.sendall(command.encode("utf-8"))
            received_data = b""
            while True:
                data_chunk = client_socket.recv(1024)
                if not data_chunk:
                    break
                received_data += data_chunk
            # Receive data from the server
            data = received_data.decode()
            if data.startswith("[Error] > "):
                raise Exception(data)
            return data
        finally:
            if client_socket:
                client_socket.close()
