#! /usr/bin/python3
import argparse
import collections
import io
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import textwrap
import threading
from abc import ABC, abstractmethod
from enum import Enum
from time import sleep

DEFAULT_CONFIGURATION_FILE_PATH = "/etc/fw-fanctrl/config.json"
SOCKETS_FOLDER_PATH = "/run/fw-fanctrl"
COMMANDS_SOCKET_FILE_PATH = os.path.join(SOCKETS_FOLDER_PATH, ".fw-fanctrl.commands.sock")


class CommandParser:
    isRemote = True

    legacyParser = None
    parser = None

    def __init__(self, isRemote=False):
        self.isRemote = isRemote
        self.initParser()
        self.initLegacyParser()

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
            choices=["unix"],
            default="unix"
        )
        self.parser.add_argument(
            "--output-format",
            help="the output format to use for the command result",
            type=lambda s: (lambda: OutputFormat[s])() if hasattr(OutputFormat, s) else s,
            choices=list(OutputFormat._member_names_),
            default=OutputFormat.NATURAL
        )

        commandsSubParser = self.parser.add_subparsers(dest="command")
        commandsSubParser.required = True

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
            description="print the selected information",
            formatter_class=argparse.RawTextHelpFormatter
        )
        printCommand.add_argument(
            "print_selection",
            help=f"all - All details{os.linesep}current - The current strategy{os.linesep}list - List available strategies{os.linesep}speed - The current fan speed percentage{os.linesep}active - The service activity status",
            nargs="?",
            type=str,
            choices=["all",
                     "active",
                     "current",
                     "list",
                     "speed"],
            default="all"
        )

    def initLegacyParser(self):
        self.legacyParser = argparse.ArgumentParser(add_help=False)

        # avoid collision with the new parser commands
        def excludedPositionalArguments(value):
            if value in ["run", "use", "reload", "reset", "pause", "resume", "print"]:
                raise argparse.ArgumentTypeError("%s is an excluded value" % value)
            return value

        bothGroup = self.legacyParser.add_argument_group("both")
        bothGroup.add_argument(
            "_strategy",
            nargs="?",
            type=excludedPositionalArguments
        )
        bothGroup.add_argument(
            "--strategy",
            nargs="?"
        )

        runGroup = self.legacyParser.add_argument_group("run")
        runGroup.add_argument(
            "--run",
            action="store_true"
        )
        runGroup.add_argument(
            "--config",
            type=str,
            default=DEFAULT_CONFIGURATION_FILE_PATH
        )
        runGroup.add_argument(
            "--no-log",
            action="store_true"
        )
        commandGroup = self.legacyParser.add_argument_group("configure")
        commandGroup.add_argument(
            "--query",
            "-q",
            action="store_true"
        )
        commandGroup.add_argument(
            "--list-strategies",
            action="store_true"
        )
        commandGroup.add_argument(
            "--reload",
            "-r",
            action="store_true"
        )
        commandGroup.add_argument(
            "--pause",
            action="store_true"
        )
        commandGroup.add_argument(
            "--resume",
            action="store_true"
        )
        commandGroup.add_argument(
            "--hardware-controller",
            "--hc",
            type=str,
            choices=["ectool"],
            default="ectool"
        )
        commandGroup.add_argument(
            "--socket-controller",
            "--sc",
            type=str,
            choices=["unix"],
            default="unix"
        )

    def parseArgs(self, args=None):
        values = None
        original_stderr = sys.stderr
        # silencing legacy parser output
        sys.stderr = open(os.devnull, 'w')
        try:
            legacy_values = self.legacyParser.parse_args(args)
            if legacy_values.strategy is None:
                legacy_values.strategy = legacy_values._strategy
            # converting legacy values into new ones
            values = argparse.Namespace()
            values.socket_controller = legacy_values.socket_controller
            values.output_format = OutputFormat.NATURAL
            if legacy_values.query:
                values.command = "print"
                values.print_selection = "current"
            if legacy_values.list_strategies:
                values.command = "print"
                values.print_selection = "list"
            if legacy_values.resume:
                values.command = "resume"
            if legacy_values.pause:
                values.command = "pause"
            if legacy_values.reload:
                values.command = "reload"
            if legacy_values.run:
                values.command = "run"
                values.silent = legacy_values.no_log
                values.hardware_controller = legacy_values.hardware_controller
                values.config = legacy_values.config
                values.strategy = legacy_values.strategy
            if not hasattr(values, "command") and legacy_values.strategy is not None:
                values.command = "use"
                values.strategy = legacy_values.strategy
            if not hasattr(values, "command"):
                raise UnknownCommandException("not a valid legacy command")
            if self.isRemote or values.command == "run":
                # Legacy commands do not support other formats than NATURAL, so there is no need to use a CommandResult.
                print(
                    "[Warning] > this command is deprecated and will be removed soon, please use the new command format instead ('fw-fanctrl -h' for more details).")
        except (SystemExit, Exception):
            sys.stderr = original_stderr
            values = self.parser.parse_args(args)
        finally:
            sys.stderr = original_stderr
        return values


class JSONException(Exception):
    pass


class UnimplementedException(Exception):
    pass


class InvalidStrategyException(Exception):
    pass


class SocketAlreadyRunningException(Exception):
    pass


class UnknownCommandException(Exception):
    pass


class SocketCallException(Exception):
    pass


class CommandStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class OutputFormat(str, Enum):
    NATURAL = "NATURAL"
    JSON = "JSON"


class CommandResult:
    def __init__(self, status, reason="Unexpected"):
        self.status = status
        if status == CommandStatus.ERROR:
            self.reason = reason

    def __str__(self):
        return "Success!" if self.status == CommandStatus.SUCCESS else f"[Error] > An error occurred: {self.reason}"

    def toOutputFormat(self, outputFormat):
        if outputFormat == OutputFormat.JSON:
            return json.dumps(self.__dict__)
        else:
            return str(self)


class StrategyChangeCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Strategy in use: '{self.strategy}'"


class StrategyResetCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Strategy reset to default! Strategy in use: '{self.strategy}'"


class ConfigurationReloadCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Reloaded with success! Strategy in use: '{self.strategy}'"


class ServicePauseCommandResult(CommandResult):
    def __init__(self):
        super().__init__(CommandStatus.SUCCESS)

    def __str__(self):
        return "Service paused! The hardware fan control will take over"


class ServiceResumeCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Service resumed! Strategy in use: '{self.strategy}'"


class PrintActiveCommandResult(CommandResult):
    def __init__(self, active):
        super().__init__(CommandStatus.SUCCESS)
        self.active = active

    def __str__(self):
        return f"Active: {self.active}"


class PrintCurrentStrategyCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Strategy in use: '{self.strategy}'"


class PrintStrategyListCommandResult(CommandResult):
    def __init__(self, strategies):
        super().__init__(CommandStatus.SUCCESS)
        self.strategies = strategies

    def __str__(self):
        return f"Strategy list: {os.linesep}- {f"{os.linesep}- ".join(self.strategies)}"


class PrintFanSpeedCommandResult(CommandResult):
    def __init__(self, speed):
        super().__init__(CommandStatus.SUCCESS)
        self.speed = speed

    def __str__(self):
        return f"Current fan speed: '{self.speed}%'"


class RuntimeResult(CommandResult):
    def __init__(self, status, reason="Unexpected"):
        super().__init__(status, reason)


class StatusRuntimeResult(RuntimeResult):
    def __init__(self, strategy, speed, temperature, movingAverageTemperature, effectiveTemperature, active):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy
        self.speed = speed
        self.temperature = temperature
        self.movingAverageTemperature = movingAverageTemperature
        self.effectiveTemperature = effectiveTemperature
        self.active = active

    def __str__(self):
        return f"Strategy: '{self.strategy}'{os.linesep}Speed: {self.speed}%{os.linesep}Temp: {self.temperature}°C{os.linesep}MovingAverageTemp: {self.movingAverageTemperature}°C{os.linesep}EffectiveTemp: {self.effectiveTemperature}°C{os.linesep}Active: {self.active}"


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
                        client_socket.sendall(commandResult.toOutputFormat(args.output_format).encode('utf-8'))
                    else:
                        naturalResult = commandResult.toOutputFormat(args.output_format)
                        if parsePrintCapture.getvalue().strip():
                            naturalResult = parsePrintCapture.getvalue() + naturalResult
                        client_socket.sendall(naturalResult.encode('utf-8'))
                except (SystemExit, Exception) as e:
                    _cre = (
                        CommandResult(CommandStatus.ERROR, f"An error occurred while treating a socket command: {e}")
                        .toOutputFormat(getattr(args, "output_format", None)))
                    print(_cre, file=sys.stderr)
                    client_socket.sendall(_cre.encode('utf-8'))
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
            client_socket.sendall(command.encode('utf-8'))
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
        # Empty for ectool, as setting an arbitrary speed disables the automatic fan control
        pass


class FanController:
    hardwareController = None
    socketController = None
    configuration = None
    overwrittenStrategy = None
    outputFormat = None
    speed = 0
    tempHistory = collections.deque([0] * 100, maxlen=100)
    active = True
    timecount = 0

    def __init__(self, hardwareController, socketController, configPath, strategyName, outputFormat):
        self.hardwareController = hardwareController
        self.socketController = socketController
        self.configuration = Configuration(configPath)

        if strategyName is not None and strategyName != "":
            self.overwriteStrategy(strategyName)

        self.outputFormat = outputFormat

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
            return StrategyResetCommandResult(self.getCurrentStrategy().name)
        elif args.command == "use":
            try:
                self.overwriteStrategy(args.strategy)
                return StrategyChangeCommandResult(self.getCurrentStrategy().name)
            except InvalidStrategyException:
                raise InvalidStrategyException(f"The specified strategy is invalid: {args.strategy}")
        elif args.command == "reload":
            if self.configuration.reload():
                if self.overwrittenStrategy is not None:
                    self.overwriteStrategy(self.overwrittenStrategy.name)
            else:
                raise JSONException("Config file could not be parsed due to JSON Error")
            return ConfigurationReloadCommandResult(self.getCurrentStrategy().name)
        elif args.command == "pause":
            self.pause()
            return ServicePauseCommandResult()
        elif args.command == "resume":
            self.resume()
            return ServiceResumeCommandResult(self.getCurrentStrategy().name)
        elif args.command == "print":
            if args.print_selection == "all":
                return self.dumpDetails()
            elif args.print_selection == "active":
                return PrintActiveCommandResult(self.active)
            elif args.print_selection == "current":
                return PrintCurrentStrategyCommandResult(self.getCurrentStrategy().name)
            elif args.print_selection == "list":
                return PrintStrategyListCommandResult(list(self.configuration.getStrategies()))
            elif args.print_selection == "speed":
                return PrintFanSpeedCommandResult(str(self.speed))
        raise UnknownCommandException(f"Unknown command: '{args.command}', unexpected.")

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

    def dumpDetails(self):
        currentStrategy = self.getCurrentStrategy()
        currentTemperture = self.getActualTemperature()
        movingAverageTemp = self.getMovingAverageTemperature(currentStrategy.movingAverageInterval)
        effectiveTemp = self.getEffectiveTemperature(currentTemperture, currentStrategy.movingAverageInterval)

        return StatusRuntimeResult(currentStrategy.name, self.speed, currentTemperture,
                                     movingAverageTemp, effectiveTemp, self.active)

    def printState(self):
        print(self.dumpDetails().toOutputFormat(self.outputFormat))

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
            _rte = RuntimeResult(CommandStatus.ERROR, f"Missing strategy, exiting for safety reasons: {e.args[0]}")
            print(_rte.toOutputFormat(self.outputFormat), file=sys.stderr)
        except Exception as e:
            _rte = RuntimeResult(CommandStatus.ERROR, f"Critical error, exiting for safety reasons: {e}")
            print(_rte.toOutputFormat(self.outputFormat), file=sys.stderr)
        exit(1)


def main():
    try:
        args = CommandParser().parseArgs()
    except Exception as e:
        _cre = CommandResult(CommandStatus.ERROR, str(e))
        print(_cre.toOutputFormat(OutputFormat.NATURAL), file=sys.stderr)
        exit(1)

    socketController = UnixSocketController()
    if args.socket_controller == "unix":
        socketController = UnixSocketController()

    if args.command == "run":
        hardwareController = EctoolHardwareController(noBatterySensorMode=args.no_battery_sensors)
        if args.hardware_controller == "ectool":
            hardwareController = EctoolHardwareController(noBatterySensorMode=args.no_battery_sensors)

        fan = FanController(hardwareController=hardwareController, socketController=socketController,
                            configPath=args.config, strategyName=args.strategy,
                            outputFormat=getattr(args, "output_format", None))
        fan.run(debug=not args.silent)
    else:
        try:
            commandResult = socketController.sendViaClientSocket(' '.join(sys.argv[1:]))
            if commandResult:
                print(commandResult)
        except Exception as e:
            if str(e).startswith("[Error] >"):
                print(str(e), file=sys.stderr)
            else:
                _cre = CommandResult(CommandStatus.ERROR, str(e))
                print(_cre.toOutputFormat(getattr(args, "output_format", None)), file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    main()
