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
from abc import ABC, abstractmethod
from time import sleep
from pathlib import Path
from typing import Optional, Deque, List

DEFAULT_CONFIGURATION_FILE_PATH = "/etc/fw-fanctrl/config.json"
SOCKETS_FOLDER_PATH = "/run/fw-fanctrl"
COMMANDS_SOCKET_FILE_PATH = os.path.join(SOCKETS_FOLDER_PATH, ".fw-fanctrl.commands.sock")

parser = argparse.ArgumentParser(
    description="Control Framework's laptop fan with a speed curve",
)

bothGroup = parser.add_argument_group("both")
bothGroup.add_argument(
    "_strategy",
    nargs="?",
    help='Name of the strategy to use e.g: "lazy" (check config.json for others). '
         'Use "defaultStrategy" to go back to the default strategy',
)
bothGroup.add_argument(
    "--strategy",
    nargs="?",
    help='Name of the strategy to use e.g: "lazy" (check config.json for others). '
         'Use "defaultStrategy" to go back to the default strategy',
)

runGroup = parser.add_argument_group("run")
runGroup.add_argument("--run", help="run the service", action="store_true")
runGroup.add_argument("--config", type=str, help="Path to config file",
                      default=DEFAULT_CONFIGURATION_FILE_PATH)
runGroup.add_argument(
    "--no-log", help="Disable print speed/meanTemp to stdout", action="store_true"
)
commandGroup = parser.add_argument_group("configure")
commandGroup.add_argument(
    "--query", "-q", help="Query the currently active strategy", action="store_true"
)
commandGroup.add_argument(
    "--list-strategies", "-l", help="List the available strategies", action="store_true"
)
commandGroup.add_argument(
    "--reload", "-r", help="Reload the configuration from file", action="store_true"
)
commandGroup.add_argument("--pause", help="Pause the program", action="store_true")
commandGroup.add_argument("--resume", help="Resume the program", action="store_true")


class InvalidStrategyException(Exception):
    pass


class KModNotWorkingException(Exception):
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
            self.data = json.load(fp)

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

    def getMode(self):
        if "mode" in self.data and self.data["mode"].lower() == "kmod":
            return "kmod"
        return "ectool"

    def getUseGPU(self):
        if "useGPU" in self.data and self.data["useGPU"].lower() in ["yes", "y", "true", "t", "1"]:
            return True
        return False


class FanController(ABC):
    configuration: Configuration = None
    overwrittenStrategy: Optional[Strategy] = None
    speed: int = None
    active: bool = True
    timecount: int = 0
    tempHistory: Deque = collections.deque([0] * 100, maxlen=100)

    def __init__(self, config: Configuration):
        self.configuration = config

    def overwriteStrategy(self, strategyName):
        self.overwrittenStrategy = self.configuration.getStrategy(strategyName)
        self.timecount = 0

    def clearOverwrittenStrategy(self):
        self.overwrittenStrategy = None
        self.timecount = 0

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def setSpeed(self, speed: int) -> None:
        pass

    @abstractmethod
    def getRawTemperatures(self) -> List[float]:
        pass

    def resume(self):
        self.active = True

    def bindSocket(self):
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(COMMANDS_SOCKET_FILE_PATH):
            os.remove(COMMANDS_SOCKET_FILE_PATH)
        try:
            if not os.path.exists(SOCKETS_FOLDER_PATH):
                os.makedirs(SOCKETS_FOLDER_PATH)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(COMMANDS_SOCKET_FILE_PATH)
            os.chmod(COMMANDS_SOCKET_FILE_PATH, 0o777)
            server_socket.listen(1)
            while True:
                client_socket, _ = server_socket.accept()
                try:
                    # Receive data from the client
                    data = client_socket.recv(4096).decode()
                    print("Received command:", data)

                    args = parser.parse_args(shlex.split(data))
                    if args.strategy or args._strategy:
                        strategy = args.strategy
                        if strategy is None:
                            strategy = args._strategy
                        try:
                            if strategy == "defaultStrategy":
                                self.clearOverwrittenStrategy()
                            else:
                                self.overwriteStrategy(strategy)
                            client_socket.sendall(self.getCurrentStrategy().name.encode())
                        except InvalidStrategyException:
                            client_socket.sendall(("Error: unknown strategy: " + strategy).encode())
                    if args.pause:
                        self.pause()
                        client_socket.sendall("Success".encode())
                    if args.resume:
                        self.resume()
                        client_socket.sendall("Success".encode())
                    if args.query:
                        client_socket.sendall(self.getCurrentStrategy().name.encode())
                    if args.list_strategies:
                        client_socket.sendall('\n'.join(self.configuration.getStrategies()).encode())
                    if args.reload:
                        self.configuration.reload()
                        if self.overwrittenStrategy is not None:
                            self.overwriteStrategy(self.overwrittenStrategy.name)
                        client_socket.sendall("Success".encode())
                except:
                    pass
                finally:
                    client_socket.shutdown(socket.SHUT_WR)
                    client_socket.close()
        finally:
            server_socket.close()

    def getCurrentStrategy(self):
        if self.overwrittenStrategy is not None:
            return self.overwrittenStrategy
        if self.getBatteryChargingStatus():
            return self.configuration.getDefaultStrategy()
        return self.configuration.getDischargingStrategy()

    def getBatteryChargingStatus(self):
        bashCommand = "ectool battery"
        rawOut = subprocess.run(bashCommand, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True,
                                text=True).stdout
        return len(re.findall(r'Flags.*(AC_PRESENT)', rawOut)) > 0

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
            f"speed: {self.speed}%, temp: {currentTemperture}°C, "
            f"movingAverageTemp: {self.getMovingAverageTemperature(currentStrategy.movingAverageInterval)}°C, "
            f"effectureTemp: {self.getEffectiveTemperature(currentTemperture, currentStrategy.movingAverageInterval)}°C"
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

    def getActualTemperature(self):
        temps = sorted([x for x in [float(x) for x in self.getRawTemperatures()] if x > 0], reverse=True)

        # safety fallback to avoid damaging hardware
        if len(temps) == 0:
            return 50

        return round(temps[0], 1)


class FanControllerKmod(FanController):
    get_fanspeed_files: List[Path]
    set_fanspeed_files: List[Path]
    reset_to_auto_files: List[Path]
    get_temp_files: List[Path]

    def __init__(self, config: Configuration, strategyName: str):
        super().__init__(config)

        self.sysfs_get_fanspeed_files = []
        self.sysfs_set_fanspeed_files = []
        self.sysfs_reset_to_auto_files = []
        self.sysfs_get_temp = []

        fan_ctrl_base_dir = Path('/sys/class/hwmon')
        if not fan_ctrl_base_dir.exists() or not fan_ctrl_base_dir.is_dir():
            raise KModNotWorkingException(f"{str(fan_ctrl_base_dir)} does not exist or is not a directory")

        for hwmon_interface in fan_ctrl_base_dir.iterdir():
            name_file = hwmon_interface / "name"
            with name_file.open("r") as name_fp:
                device_name = name_fp.read().strip()
            if device_name == "framework_laptop":
                for file in hwmon_interface.iterdir():
                    if file.name.startswith("fan") and file.name.endswith("_target"):
                        self.sysfs_get_fanspeed_files.append(file)
                    if file.name.startswith("pwm"):
                        if file.name[3:].isdecimal():
                            self.sysfs_set_fanspeed_files.append(file)
                        elif file.name.endswith("_enable"):
                            self.sysfs_reset_to_auto_files.append(file)
            elif device_name == "acpitz":
                for file in hwmon_interface.iterdir():
                    if file.name.startswith("temp") and file.name.endswith("_input"):
                        self.sysfs_get_temp.append(file)
            elif self.configuration.getUseGPU() and device_name == "amdgpu":
                for file in hwmon_interface.iterdir():
                    if file.name.startswith("temp") and file.name.endswith("_input"):
                        self.sysfs_get_temp.append(file)
        if len(self.sysfs_get_fanspeed_files) == 0 and len(self.sysfs_set_fanspeed_files) == 0 \
                and len(self.sysfs_reset_to_auto_files) == 0 and len(self.sysfs_get_temp) == 0:
            raise KModNotWorkingException(f"Could not find files necessary to control fans")

        if strategyName is not None and strategyName != "":
            self.overwriteStrategy(strategyName)
            t = threading.Thread(target=self.bindSocket)
            t.daemon = True
            t.start()

    def pause(self):
        for file in self.sysfs_reset_to_auto_files:
            with file.open("w") as fp:
                fp.write("2\n")

    def setSpeed(self, speed: int) -> None:
        self.speed = speed
        for file in self.sysfs_set_fanspeed_files:
            with file.open("w") as fp:
                fp.write(f"{speed}\n")

    def getRawTemperatures(self) -> List[float]:
        rawTemps = []
        for file in self.sysfs_get_temp:
            with file.open("r") as fp:
                rawTemps.append(float(fp.read()) / 1000.0)
        return rawTemps


class FanControllerEcTool(FanController):
    def __init__(self, config: Configuration, strategyName):
        super().__init__(config)
        if strategyName is not None and strategyName != "":
            self.overwriteStrategy(strategyName)
            t = threading.Thread(target=self.bindSocket)
            t.daemon = True
            t.start()

    def pause(self):
        self.active = False
        bashCommand = f"ectool autofanctrl"
        subprocess.run(bashCommand, stdout=subprocess.PIPE, shell=True)

    def setSpeed(self, speed):
        self.speed = speed
        bashCommand = f"ectool fanduty {speed}"
        subprocess.run(bashCommand, stdout=subprocess.PIPE, shell=True)

    def getRawTemperatures(self) -> List[float]:
        bashCommand = "ectool temps all"
        rawOut = subprocess.run(bashCommand, stdout=subprocess.PIPE, shell=True, text=True).stdout
        return re.findall(r'\(= (\d+) C\)', rawOut)


def main():
    args = parser.parse_args()

    if args.run:
        strategy = args.strategy
        if strategy is None:
            strategy = args._strategy
        config = Configuration(args.config)
        mode = config.getMode()
        if mode == "kmod":
            fan = FanControllerKmod(config=config, strategyName=args.strategy)
        else:
            fan = FanControllerEcTool(config=config, strategyName=args.strategy)
        fan.run(debug=not args.no_log)
    else:
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client_socket.connect(COMMANDS_SOCKET_FILE_PATH)
            client_socket.sendall(' '.join(sys.argv[1:]).encode())
            received_data = b""
            while True:
                data_chunk = client_socket.recv(1024)
                if not data_chunk:
                    break
                received_data += data_chunk
            # Receive data from the server
            data = received_data.decode()
            print(data)
            if data.startswith("Error:"):
                exit(1)
        finally:
            if client_socket:
                client_socket.close()


if __name__ == "__main__":
    main()
