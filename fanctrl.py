#! /usr/bin/python3

import argparse
import subprocess
from time import sleep
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FileModifiedHandler(FileSystemEventHandler):
    def __init__(self, path, file_name, callback):
        self.file_name = file_name
        self.callback = callback

        # set observer to watch for changes in the directory
        self.observer = Observer()
        self.observer.schedule(self, path, recursive=False)
        self.observer.start()

    def on_modified(self, event):
        # only act on the change that we're looking for
        if not event.is_directory and event.src_path.endswith(self.file_name):
            self.callback()  # call callback


class FanController:
    # state
    speed = 0
    temps = [0] * 100
    _tempIndex = 0
    lastBatteryStatus = ""
    switchableFanCurve = False

    def __init__(self, configPath, strategy):
        # parse config file
        with open(configPath, "r") as fp:
            self.config = json.load(fp)
        if strategy == "":
            strategyOnCharging = self.config["defaultStrategy"]
        else:
            strategyOnCharging = strategy

        self.strategyOnCharging = self.config["strategies"][strategyOnCharging]
        # if the user didnt specify a separate strategy for discharging, use the same strategy as for charging
        strategyOnDischarging = self.config["strategyOnDischarging"]
        if strategyOnDischarging == "":
            self.switchableFanCurve = False
            self.strategyOnDischarging = self.strategyOnCharging
        else:
            self.strategyOnDischarging = self.config["strategies"][
                strategyOnDischarging
            ]
            self.switchableFanCurve = True
            self.batteryChargingStatusPath = self.config["batteryChargingStatusPath"]
            if self.batteryChargingStatusPath == "":
                self.batteryChargingStatusPath = "/sys/class/power_supply/BAT1/status"

        self.setStrategy(self.strategyOnCharging)

        FileModifiedHandler("/tmp/", ".fw-fanctrl.tmp", self.strategyLiveUpdate)

    def setStrategy(self, strategy):
        self.speedCurve = strategy["speedCurve"]
        self.fanSpeedUpdateFrequency = strategy["fanSpeedUpdateFrequency"]
        self.movingAverageInterval = strategy["movingAverageInterval"]
        self.setSpeed(self.speedCurve[0]["speed"])
        self.updateTemperature()
        self.temps = [self.temps[self._tempIndex]] * 100

    def switchStrategy(self):
        update = self.getBatteryChargingStatus()
        if update == 0:
            return  # if charging status unchanged do nothing
        elif update == 1:
            strategy = self.strategyOnCharging
        elif update == 2:
            strategy = self.strategyOnDischarging

        # load fan curve according to strategy
        self.setStrategy(strategy)

    def strategyLiveUpdate(self):
        with open("/tmp/.fw-fanctrl.tmp", "r+") as fp:
            strategy = fp.read()
            fp.seek(0)
            fp.truncate

            if strategy == "defaultStrategy":
                strategy = self.config["defaultStrategy"]

            if strategy in self.config["strategies"]:
                self.setStrategy(self.config["strategies"][strategy])
            else:
                fp.write("unknown strategy")

    def getBatteryChargingStatus(self):
        with open(self.batteryChargingStatusPath, "r") as fb:
            currentBatteryStatus = fb.readline().rstrip("\n")

            if currentBatteryStatus == self.lastBatteryStatus:
                return 0  # battery charging status hasnt change - dont switch fan curve
            self.lastBatteryStatus = currentBatteryStatus
            if currentBatteryStatus == "Discharging":
                return 2
            # Battery is not discharging
            return 1

    def setSpeed(self, speed):
        self.speed = speed
        bashCommand = f"ectool fanduty {speed}"
        subprocess.run(bashCommand, stdout=subprocess.PIPE, shell=True)

    def adaptSpeed(self):
        currentTemp = self.temps[self._tempIndex]
        currentTemp = min(
            currentTemp, self.getMovingAverageTemperature(self.movingAverageInterval)
        )
        minPoint = self.speedCurve[0]
        maxPoint = self.speedCurve[-1]
        for e in self.speedCurve:
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
        self.setSpeed(newSpeed)

    def updateTemperature(self):
        sumCoreTemps = 0
        sensorsOutput = json.loads(
            subprocess.run(
                "sensors -j &> /dev/null",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                executable="/bin/bash",
            ).stdout
        )

        # sensors -j does not return the core temperatures at startup
        if "coretemp-isa-0000" not in sensorsOutput.keys():
            return

        cores = 0
        for k, v in sensorsOutput["coretemp-isa-0000"].items():
            if k.startswith("Core "):
                i = int(k.split(" ")[1])
                cores += 1
                sumCoreTemps += float(v[[key for key in v.keys() if key.endswith("_input")][0]])

        self._tempIndex = (self._tempIndex + 1) % len(self.temps)
        self.temps[self._tempIndex] = sumCoreTemps / cores

    # return mean temperature over a given time interval (in seconds)
    def getMovingAverageTemperature(self, timeInterval):
        tempSum = 0
        for i in range(0, timeInterval):
            tempSum += self.temps[self._tempIndex - i]
        return tempSum / timeInterval

    def printState(self):
        print(
            f"speed: {self.speed}% temp: {self.temps[self._tempIndex]}°C movingAverage: {round(self.getMovingAverageTemperature(self.movingAverageInterval), 2)}°C"
        )

    def run(self, debug=True):
        while True:
            if self.switchableFanCurve:
                self.switchStrategy()
            self.updateTemperature()

            # update fan speed every "fanSpeedUpdateFrequency" seconds
            if self._tempIndex % self.fanSpeedUpdateFrequency == 0:
                self.adaptSpeed()

            if debug:
                self.printState()

            sleep(1)


def main():
    parser = argparse.ArgumentParser(
        description="Control Framework's laptop fan with a speed curve",
    )
    parser.add_argument(
        "new_strategy",
        nargs="?",
        help="Switches the strategy of a currently running fw-fanctrl instance",
    )
    parser.add_argument("--config", type=str, help="Path to config file", default=".")
    parser.add_argument(
        "--strategy",
        type=str,
        help='Name of the strategy to use e.g: "lazy" (check config.json for others)',
        default="",
    )
    parser.add_argument(
        "--no-log", help="Print speed/meanTemp to stdout", action="store_true"
    )
    args = parser.parse_args()

    if args.new_strategy:
        with open("/tmp/.fw-fanctrl.tmp", "w") as fp:
            fp.write(args.new_strategy)
        sleep(0.1)
        with open("/tmp/.fw-fanctrl.tmp", "r") as fp:
            if fp.read() == "unknown strategy":
                print("Error: unknown strategy")
    else:
        fan = FanController(configPath=args.config, strategy=args.strategy)
        fan.run(debug=not args.no_log)


if __name__ == "__main__":
    main()
