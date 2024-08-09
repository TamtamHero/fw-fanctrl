#! /usr/bin/python3
import argparse
import collections
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import threading
from time import sleep
from abc import ABC, abstractmethod

DEFAULT_CONFIGURATION_FILE_PATH = "/etc/fw-fanctrl/config.json"
WINDOWS_SOCKET_PATH = r"\\.\pipe\fw-fanctrl.socket"

parser = None


class JSONException(Exception):
    pass


class UnimplementedException(Exception):
    pass


class InvalidStrategyException(Exception):
    pass


class SocketAlreadyRunningException(Exception):
    pass


class Strategy:
    name = None
    fanSpeedUpdateFrequency = None
    movingAverageInterval = None
    speedCurve = None

    def __init__(self, name, parameters):
        self.name = name
        self.fanSpeedUpdateFrequency = parameters["fanSpeedUpdateFrequency"]
        if self.fanSpeedUpdateFrequency is None or self.fanSpeedUpdateFrequency == "":
            self.fanSpeedUpdateFrequency = 5
        self.movingAverageInterval = parameters["movingAverageInterval"]
        if self.movingAverageInterval is None or self.movingAverageInterval == "":
            self.movingAverageInterval = 20
        self.speedCurve = parameters["speedCurve"]


class Configuration:
    path = None
    data: None

    def __init__(self, path):
        self.path = path
        self.reload()

    def reload(self):
        with open(self.path, "r") as fp:
            try:
                self.data = json.load(fp)
            except json.JSONDecodeError:
                return False
        return True

    def getStrategies(self):
        return self.data["strategies"].keys()

    def getStrategy(self, strategyName):
        if strategyName == "strategyOnDischarging":
            strategyName = self.data[strategyName]
            if strategyName == "":
                strategyName = "defaultStrategy"
        if strategyName == "defaultStrategy":
            strategyName = self.data[strategyName]
        if strategyName is None or strategyName not in self.data["strategies"]:
            raise InvalidStrategyException(strategyName)
        return Strategy(strategyName, self.data["strategies"][strategyName])

    def getDefaultStrategy(self):
        return self.getStrategy("defaultStrategy")

    def getDischargingStrategy(self):
        return self.getStrategy("strategyOnDischarging")


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


class WindowsSocketController(SocketController, ABC):
    import ctypes
    from ctypes import wintypes, windll

    _ctypes = ctypes

    CreateNamedPipe = windll.kernel32.CreateNamedPipeW
    ConnectNamedPipe = windll.kernel32.ConnectNamedPipe
    DisconnectNamedPipe = windll.kernel32.DisconnectNamedPipe
    CreateFile = windll.kernel32.CreateFileW
    ReadFile = windll.kernel32.ReadFile
    WriteFile = windll.kernel32.WriteFile
    CloseHandle = windll.kernel32.CloseHandle

    LPSECURITY_ATTRIBUTES = ctypes.c_void_p
    LPDWORD = ctypes.POINTER(wintypes.DWORD)
    LPVOID = ctypes.c_void_p
    DWORD = wintypes.DWORD

    server_socket = None

    def startServerSocket(self, commandCallback=None):
        if self.server_socket:
            raise SocketAlreadyRunningException(self.server_socket)
        self.server_socket = self.CreateNamedPipe(
            WINDOWS_SOCKET_PATH,
            self.ctypes.wintypes.DWORD(3),  # PIPE_ACCESS_DUPLEX
            self.ctypes.wintypes.DWORD(4),  # PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT
            1,  # nMaxInstances
            65536,  # nOutBufferSize
            65536,  # nInBufferSize
            0,  # nDefaultTimeOut
            None  # lpSecurityAttributes
        )
        try:
            while True:
                self.ConnectNamedPipe(self.server_socket, None)
                try:
                    # Receive data from the client
                    buffer = self.ctypes.create_string_buffer(65536)
                    bytes_read = self.ctypes.wintypes.DWORD(0)
                    self.ReadFile(self.server_socket, buffer, 65536, self.ctypes.byref(bytes_read), None)
                    data = buffer.raw[:bytes_read.value].decode('utf-8')

                    args = parser.parse_args(shlex.split(data))
                    commandReturn = commandCallback(args)
                    if not commandReturn:
                        commandReturn = "Success!"

                    commandReturn = commandReturn.encode('utf-8')
                    bytes_written = self.ctypes.wintypes.DWORD(0)
                    self.WriteFile(self.server_socket, commandReturn, len(commandReturn),
                                   self.ctypes.byref(bytes_written), None)
                except Exception as e:
                    message = f"[Error] > An error occurred: {e}".encode('utf-8')
                    bytes_written = self.wintypes.DWORD(0)
                    self.WriteFile(self.server_socket, message, len(message), self.ctypes.byref(bytes_written), None)
                finally:
                    self.DisconnectNamedPipe(self.server_socket)
        finally:
            self.stopServerSocket()

    def stopServerSocket(self):
        if self.server_socket:
            self.CloseHandle(self.server_socket)
            self.server_socket = None

    def isServerSocketRunning(self):
        return self.server_socket is not None

    def sendViaClientSocket(self, command):
        client_socket = self.CreateFile(
            WINDOWS_SOCKET_PATH,
            self.ctypes.wintypes.DWORD(0x00000003),  # GENERIC_READ | GENERIC_WRITE
            0,
            None,
            self.ctypes.wintypes.DWORD(3),  # OPEN_EXISTING
            0,
            None
        )
        try:
            message = command.encode('utf-8')
            bytes_written = self.ctypes.wintypes.DWORD(0)
            self.WriteFile(client_socket, message, len(message), self.ctypes.byref(bytes_written), None)
            buffer = self.ctypes.create_string_buffer(65536)
            bytes_read = self.ctypes.wintypes.DWORD(0)
            self.ReadFile(client_socket, buffer, 65536, self.ctypes.byref(bytes_read), None)
            data = buffer.raw[:bytes_read.value].decode('utf-8')
            if data.startswith("[Error] > "):
                raise Exception(data)
            return data
        finally:
            self.CloseHandle(client_socket)


class HardwareController(ABC):
    @abstractmethod
    def getTemperature(self):
        raise UnimplementedException()

    @abstractmethod
    def setSpeed(self, speed):
        raise UnimplementedException()

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def resume(self):
        pass

    @abstractmethod
    def isOnAC(self):
        raise UnimplementedException()


class EctoolHardwareController(HardwareController, ABC):

    def getTemperature(self):
        rawOut = subprocess.run("ectool temps all", stdout=subprocess.PIPE, shell=True, text=True).stdout
        rawTemps = re.findall(r'\(= (\d+) C\)', rawOut)
        temps = sorted([x for x in [int(x) for x in rawTemps] if x > 0], reverse=True)
        # safety fallback to avoid damaging hardware
        if len(temps) == 0:
            return 50
        return round(temps[0], 1)

    def setSpeed(self, speed):
        subprocess.run(f"ectool fanduty {speed}", stdout=subprocess.PIPE, shell=True)

    def isOnAC(self):
        rawOut = subprocess.run("ectool battery", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True,
                                text=True).stdout
        return len(re.findall(r"Flags.*(AC_PRESENT)", rawOut)) > 0

    def pause(self):
        subprocess.run("ectool autofanctrl", stdout=subprocess.PIPE, shell=True)

    def resume(self):
        pass


class FanController:
    hardwareController = None
    socketController = None
    configuration = None
    overwrittenStrategy = None
    speed = 0
    tempHistory = collections.deque([0] * 100, maxlen=100)
    active = True
    timecount = 0

    def __init__(self, hardwareController, socketController, configPath, strategyName):
        self.hardwareController = hardwareController
        self.socketController = socketController
        self.configuration = Configuration(configPath)

        if strategyName is not None and strategyName != "":
            self.overwriteStrategy(strategyName)

        t = threading.Thread(target=self.socketController.startServerSocket, args=[self.commandManager])
        t.daemon = True
        t.start()

    def getActualTemperature(self):
        return self.hardwareController.getTemperature()

    def setSpeed(self, speed):
        self.speed = speed
        self.hardwareController.setSpeed(speed)

    def isOnAC(self):
        return self.hardwareController.isOnAC()

    def pause(self):
        self.active = False
        self.hardwareController.pause()

    def resume(self):
        self.active = True
        self.hardwareController.resume()

    def overwriteStrategy(self, strategyName):
        self.overwrittenStrategy = self.configuration.getStrategy(strategyName)
        self.timecount = 0

    def clearOverwrittenStrategy(self):
        self.overwrittenStrategy = None
        self.timecount = 0

    def getCurrentStrategy(self):
        if self.overwrittenStrategy is not None:
            return self.overwrittenStrategy
        if self.isOnAC():
            return self.configuration.getDefaultStrategy()
        return self.configuration.getDischargingStrategy()

    def commandManager(self, command):
        if command.strategy or command._strategy:
            strategy = command.strategy
            if strategy is None:
                strategy = command._strategy
            try:
                if strategy == "defaultStrategy":
                    self.clearOverwrittenStrategy()
                else:
                    self.overwriteStrategy(strategy)
                return self.getCurrentStrategy().name
            except InvalidStrategyException:
                raise InvalidStrategyException(f"The specified strategy is invalid: {strategy}")
        elif command.pause:
            self.pause()
        elif command.resume:
            self.resume()
        elif command.query:
            return self.getCurrentStrategy().name
        elif command.list_strategies:
            return '\n'.join(self.configuration.getStrategies())
        elif command.reload:
            if self.configuration.reload():
                if self.overwrittenStrategy is not None:
                    self.overwriteStrategy(self.overwrittenStrategy.name)
            else:
                raise JSONException("Config file could not be parsed due to JSON Error")

    # return mean temperature over a given time interval (in seconds)
    def getMovingAverageTemperature(self, timeInterval):
        slicedTempHistory = [x for x in self.tempHistory if x > 0][-timeInterval:]
        if len(slicedTempHistory) == 0:
            return self.getActualTemperature()
        return round(sum(slicedTempHistory) / len(slicedTempHistory), 1)

    def getEffectiveTemperature(self, currentTemp, timeInterval):
        # the moving average temperature count for 2/3 of the effective temperature
        return round(min(self.getMovingAverageTemperature(timeInterval), currentTemp), 1)

    def adaptSpeed(self, currentTemp):
        currentStrategy = self.getCurrentStrategy()
        currentTemp = self.getEffectiveTemperature(currentTemp, currentStrategy.movingAverageInterval)
        minPoint = currentStrategy.speedCurve[0]
        maxPoint = currentStrategy.speedCurve[-1]
        for e in currentStrategy.speedCurve:
            if currentTemp > e["temp"]:
                minPoint = e
            else:
                maxPoint = e
                break

        if minPoint == maxPoint:
            newSpeed = minPoint["speed"]
        else:
            slope = (maxPoint["speed"] - minPoint["speed"]) / (
                    maxPoint["temp"] - minPoint["temp"]
            )
            newSpeed = int(minPoint["speed"] + (currentTemp - minPoint["temp"]) * slope)
        if self.active:
            self.setSpeed(newSpeed)

    def printState(self):
        currentStrategy = self.getCurrentStrategy()
        currentTemperture = self.getActualTemperature()
        print(
            f"speed: {self.speed}%, temp: {currentTemperture}°C, movingAverageTemp: {self.getMovingAverageTemperature(currentStrategy.movingAverageInterval)}°C, effectureTemp: {self.getEffectiveTemperature(currentTemperture, currentStrategy.movingAverageInterval)}°C"
        )

    def run(self, debug=True):
        try:
            while True:
                if self.active:
                    temp = self.getActualTemperature()
                    # update fan speed every "fanSpeedUpdateFrequency" seconds
                    if self.timecount % self.getCurrentStrategy().fanSpeedUpdateFrequency == 0:
                        self.adaptSpeed(temp)
                        self.timecount = 0

                    self.tempHistory.append(temp)

                    if debug:
                        self.printState()
                    self.timecount += 1
                    sleep(1)
                else:
                    sleep(5)
        except InvalidStrategyException as e:
            print(f"Missing strategy, exiting for safety reasons: {e.args[0]}")
        except Exception as e:
            print(f"Critical error, exiting for safety reasons: {e}")
        exit(1)


def main():
    global parser
    parser = argparse.ArgumentParser(
        description="Control Framework's laptop fan with a speed curve",
    )

    bothGroup = parser.add_argument_group("both")
    bothGroup.add_argument(
        "_strategy",
        nargs="?",
        help='Name of the strategy to use e.g: "lazy" (check config.json for others). Use "defaultStrategy" to go '
             'back to the default strategy',
    )
    bothGroup.add_argument(
        "--strategy",
        nargs="?",
        help='Name of the strategy to use e.g: "lazy" (check config.json for others). Use "defaultStrategy" to go '
             'back to the default strategy',
    )

    runGroup = parser.add_argument_group("run")
    runGroup.add_argument("--run", help="run the service", action="store_true")
    runGroup.add_argument("--config", type=str, help="Path to config file", default=DEFAULT_CONFIGURATION_FILE_PATH)
    runGroup.add_argument(
        "--no-log", help="Disable print speed/meanTemp to stdout", action="store_true"
    )
    commandGroup = parser.add_argument_group("configure")
    commandGroup.add_argument(
        "--query", "-q", help="Query the currently active strategy", action="store_true"
    )
    commandGroup.add_argument(
        "--list-strategies", help="List the available strategies", action="store_true"
    )
    commandGroup.add_argument(
        "--reload", "-r", help="Reload the configuration from file", action="store_true"
    )
    commandGroup.add_argument("--pause", help="Pause the program", action="store_true")
    commandGroup.add_argument("--resume", help="Resume the program", action="store_true")
    commandGroup.add_argument("--hardware-controller", "--hc", help="Select the hardware controller", type=str,
                              choices=["ectool"], default="ectool")
    commandGroup.add_argument("--socket-controller", "--sc", help="Select the socket controller", type=str,
                              choices=["win32"], default="win32")

    args = parser.parse_args()

    socketController = None
    if args.socket_controller == "win32":
        socketController = WindowsSocketController()

    if args.run:
        hardwareController = None
        if args.hardware_controller == "ectool":
            hardwareController = EctoolHardwareController()

        strategy = args.strategy
        if strategy is None:
            strategy = args._strategy
        fan = FanController(hardwareController=hardwareController, socketController=socketController,
                            configPath=args.config, strategyName=args.strategy)
        fan.run(debug=not args.no_log)
    else:
        try:
            commandResult = socketController.sendViaClientSocket(' '.join(sys.argv[1:]))
            if commandResult:
                print(commandResult)
        except Exception as e:
            print(f"[Error] > An error occurred: {e}", file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    main()
