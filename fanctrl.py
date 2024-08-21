#! /usr/bin/python3
import argparse
import collections
import io
import json
import re
import shlex
import subprocess
import sys
import threading
import traceback
import textwrap
from time import sleep
from abc import ABC, abstractmethod

DEFAULT_CONFIGURATION_FILE_PATH = "%%appdata%%/fw-fanctrl/config.json"
WINDOWS_SOCKET_PATH = r"\\.\pipe\fw-fanctrl.socket"


class CommandParser:
    isRemote = True

    legacyParser = None
    parser = None

    def __init__(self, isRemote=False):
        self.isRemote = isRemote
        self.initParser()

    def initParser(self):
        self.parser = argparse.ArgumentParser(
            prog="fw-fanctrl",
            description="control Framework's laptop fan(s) with a speed curve",
            epilog=textwrap.dedent(
                "obtain more help about a command or subcommand using `fw-fanctrl <command> [subcommand...] -h/--help`"),
            formatter_class=argparse.RawTextHelpFormatter
        )
        self.parser.add_argument(
            "--socket-controller",
            "--sc",
            help="the socket controller to use for communication between the cli and the service",
            type=str,
            choices=["win32"],
            default="win32"
        )

        commandsSubParser = self.parser.add_subparsers(dest="command")

        if not self.isRemote:
            runCommand = commandsSubParser.add_parser(
                "run",
                description="run the service",
                formatter_class=argparse.RawTextHelpFormatter
            )
            runCommand.add_argument(
                "strategy",
                help='name of the strategy to use e.g: "lazy" (use `print strategies` to list available strategies)',
                nargs=argparse.OPTIONAL
            )
            runCommand.add_argument(
                "--config",
                "-c",
                help=f"the configuration file path (default: {DEFAULT_CONFIGURATION_FILE_PATH})",
                type=str,
                default=DEFAULT_CONFIGURATION_FILE_PATH
            )
            runCommand.add_argument(
                "--silent",
                "-s",
                help="disable printing speed/temp status to stdout",
                action="store_true"
            )
            runCommand.add_argument(
                "--hardware-controller",
                "--hc",
                help="the hardware controller to use for fetching and setting the temp and fan(s) speed",
                type=str,
                choices=["ectool"],
                default="ectool"
            )
            runCommand.add_argument(
                "--no-battery-sensors",
                help="disable checking battery temperature sensors",
                action="store_true",
            )

        useCommand = commandsSubParser.add_parser(
            "use",
            description="change the current strategy"
        )
        useCommand.add_argument(
            "strategy",
            help='name of the strategy to use e.g: "lazy". (use `print strategies` to list available strategies)'
        )

        commandsSubParser.add_parser(
            "reset",
            description="reset to the default strategy"
        )
        commandsSubParser.add_parser(
            "reload",
            description="reload the configuration file"
        )
        commandsSubParser.add_parser(
            "pause",
            description="pause the service"
        )
        commandsSubParser.add_parser(
            "resume",
            description="resume the service"
        )

        printCommand = commandsSubParser.add_parser(
            "print",
            description="print the selected information"
        )
        printCommand.add_argument(
            "print_selection",
            help="what should be printed",
            nargs="?",
            type=str,
            choices=["current",
                     "list"],
            default="current"
        )

    def parseArgs(self, args=None):
        return self.parser.parse_args(args)


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
    data = None

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

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    ConvertStringSecurityDescriptorToSecurityDescriptorW = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.DWORD)]
    ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.HANDLE

    sddl_string = "D:P(A;;GA;;;WD)"

    security_descriptor = wintypes.LPVOID()
    ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl_string, 1, ctypes.byref(security_descriptor), None)

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        from ctypes import wintypes

        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", wintypes.LPVOID),
            ("nLength", wintypes.BOOL),
        ]

    security_attributes = SECURITY_ATTRIBUTES()
    security_attributes.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
    security_attributes.lpSecurityDescriptor = security_descriptor
    security_attributes.bInheritHandle = False

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
            self.ctypes.byref(self.security_attributes)  # lpSecurityAttributes
        )
        try:
            while True:
                self.ConnectNamedPipe(self.server_socket, None)
                parsePrintCapture = io.StringIO()
                try:
                    # Receive data from the client
                    buffer = self.ctypes.create_string_buffer(65536)
                    bytes_read = self.ctypes.wintypes.DWORD(0)
                    self.ReadFile(self.server_socket, buffer, 65536, self.ctypes.byref(bytes_read), None)
                    data = buffer.raw[:bytes_read.value].decode('utf-8')

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
                    commandReturn = commandReturn.encode('utf-8')
                    bytes_written = self.ctypes.wintypes.DWORD(0)
                    self.WriteFile(self.server_socket, commandReturn, len(commandReturn),
                                   self.ctypes.byref(bytes_written), None)
                except Exception as e:
                    print(f"[Error] > An error occurred while treating a socket command: {e}", file=sys.stderr)
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
    noBatterySensorMode = False
    nonBatterySensors = None
    
    def __init__(self, noBatterySensorMode=False):
        if noBatterySensorMode:
            self.noBatterySensorMode = True
            self.populateNonBatterySensors()

    def populateNonBatterySensors(self):
        self.nonBatterySensors = []
        rawOut = subprocess.run("ectool tempsinfo all", stdout=subprocess.PIPE, shell=True, text=True).stdout
        batterySensorsRaw = re.findall(r"\d+ Battery", rawOut, re.MULTILINE)
        batterySensors = [x.split(" ")[0] for x in batterySensorsRaw]
        for x in re.findall(r"^\d+", rawOut, re.MULTILINE):
            if x not in batterySensors:
                self.nonBatterySensors.append(x)

    def getTemperature(self):
        if self.noBatterySensorMode:
            rawOut = "".join([
                subprocess.run("ectool temps " + x, stdout=subprocess.PIPE, shell=True, text=True).stdout
                for x in self.nonBatterySensors
            ])
        else:
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

    def commandManager(self, args):
        if args.command == "reset" or (args.command == "use" and args.strategy == "defaultStrategy"):
            self.clearOverwrittenStrategy()
            return
        elif args.command == "use":
            try:
                self.overwriteStrategy(args.strategy)
                return self.getCurrentStrategy().name
            except InvalidStrategyException:
                raise InvalidStrategyException(f"The specified strategy is invalid: {args.strategy}")
        elif args.command == "reload":
            if self.configuration.reload():
                if self.overwrittenStrategy is not None:
                    self.overwriteStrategy(self.overwrittenStrategy.name)
            else:
                raise JSONException("Config file could not be parsed due to JSON Error")
            return
        elif args.command == "pause":
            self.pause()
            return
        elif args.command == "resume":
            self.resume()
            return
        elif args.command == "print":
            if args.print_selection == "current":
                return self.getCurrentStrategy().name
            elif args.print_selection == "list":
                return '\n'.join(self.configuration.getStrategies())
        return "Unknown command, unexpected."

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
            print(f"[Error] > Missing strategy, exiting for safety reasons: {e.args[0]}", file=sys.stderr)
        except Exception as e:
            print(f"[Error] > Critical error, exiting for safety reasons: {e}", file=sys.stderr)
            traceback.print_exc()
        exit(1)


def main():
    args = CommandParser().parseArgs()

    socketController = WindowsSocketController()
    if args.socket_controller == "win32":
        socketController = WindowsSocketController()

    if args.command == "run":
        hardwareController = EctoolHardwareController(noBatterySensorMode=args.no_battery_sensors)
        if args.hardware_controller == "ectool":
            hardwareController = EctoolHardwareController(noBatterySensorMode=args.no_battery_sensors)

        fan = FanController(hardwareController=hardwareController, socketController=socketController,
                            configPath=args.config, strategyName=args.strategy)
        fan.run(debug=not args.silent)
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
