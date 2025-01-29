import io
import os
import shlex
import socket
import sys
from abc import ABC

from fw_fanctrl import COMMANDS_SOCKET_FILE_PATH, SOCKETS_FOLDER_PATH
from fw_fanctrl.CommandParser import CommandParser
from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus
from fw_fanctrl.enum.OutputFormat import OutputFormat
from fw_fanctrl.exception.SocketAlreadyRunningException import SocketAlreadyRunningException
from fw_fanctrl.exception.SocketCallException import SocketCallException
from fw_fanctrl.socketController.SocketController import SocketController


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
                args = None
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

                        commandResult = commandCallback(args)

                        if args.output_format == OutputFormat.JSON:
                            if parsePrintCapture.getvalue().strip():
                                commandResult.info = parsePrintCapture.getvalue()
                            client_socket.sendall(commandResult.toOutputFormat(args.output_format).encode("utf-8"))
                        else:
                            naturalResult = commandResult.toOutputFormat(args.output_format)
                            if parsePrintCapture.getvalue().strip():
                                naturalResult = parsePrintCapture.getvalue() + naturalResult
                            client_socket.sendall(naturalResult.encode("utf-8"))
                except (SystemExit, Exception) as e:
                    _cre = CommandResult(
                        CommandStatus.ERROR, f"An error occurred while treating a socket command: {e}"
                    ).toOutputFormat(getattr(args, "output_format", None))
                    print(_cre, file=sys.stderr)
                    client_socket.sendall(_cre.encode("utf-8"))
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
                raise SocketCallException(data)
            return data
        finally:
            if client_socket:
                client_socket.close()
