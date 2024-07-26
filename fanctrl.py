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
SOCKETS_FOLDER_PATH = "/run/fw-fanctrl"
COMMANDS_SOCKET_FILE_PATH = os.path.join(SOCKETS_FOLDER_PATH, ".fw-fanctrl.commands.sock")

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
                try:
                    # Receive data from the client
                    data = client_socket.recv(4096).decode()
                    args = parser.parse_args(shlex.split(data))
                    commandReturn = commandCallback(args)
                    if not commandReturn:
                        commandReturn = "Success!"
                    client_socket.sendall(commandReturn.encode())
                except Exception as e:
                    client_socket.sendall(f"[Error] > An error occurred: {e}".encode())
                finally:
                    client_socket.shutdown(socket.SHUT_WR)
                    client_socket.close()
        finally:
            self.server_socket.close()

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
            client_socket.sendall(command.encode())
            received_data = b""
            while True:
                data_chunk = client_socket.recv(1024)
                if not data_chunk:
                    break
                received_data += data_chunk
            # Receive data from the server
            data = received_data.decode()
            if data.startswith("Error:"):
                raise Exception(data)
            return data
        finally:
            if client_socket:
                client_socket.close()


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
            print("Error: missing strategy, exiting for safety reasons: " + e.args[0])
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
                              choices=["unix"], default="unix")

    args = parser.parse_args()

    socketController = None
    if args.socket_controller == "unix":
        socketController = UnixSocketController()

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
            socketController.sendViaClientSocket(' '.join(sys.argv[1:]))
        except Exception as e:
            print(f"[Error] > An error occurred: {e}", file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    main()
