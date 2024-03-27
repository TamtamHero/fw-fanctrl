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
    readAttempts = 0 # only used for AMD CPUs

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

        cpuinfo = subprocess.run(
                "cat /proc/cpuinfo",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                executable="/bin/bash",
            ).stdout
        self.cpu_type = "Intel" if "GenuineIntel" in cpuinfo else "AMD"


        faninfo = subprocess.run(
                "ectool pwmgetfanrpm",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                executable="/bin/bash",
            ).stdout
        self.fan_count = faninfo.count("Fan")
        self.laptop_model = "Framework laptop 16" if self.fan_count > 1 else "Framework laptop 13"

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
        cores = 0

        sensorsOutput = json.loads(
                subprocess.run(
                    "sensors -j 2> /dev/null",
                    stdout=subprocess.PIPE,
                    shell=True,
                    text=True,
                    executable="/bin/bash",
                ).stdout
            )

        if self.cpu_type == "Intel":
            # sensors -j does not return the core temperatures at startup
            if "coretemp-isa-0000" not in sensorsOutput.keys():
                return

            for k, v in sensorsOutput["coretemp-isa-0000"].items():
                if k.startswith("Core "):
                    cores += 1
                    sumCoreTemps += float(v[[key for key in v.keys() if key.endswith("_input")][0]])

        elif self.cpu_type == "AMD":
             # sensors -j does not return the core temperatures at startup
            if "acpitz-acpi-0" in sensorsOutput.keys():
                for k, v in sensorsOutput["acpitz-acpi-0"].items():
                    # temp3 is the socket temperature, we don't have individual core temperatures when cpu is AMD
                    if k.startswith("temp3"):
                        cores += 1
                        sumCoreTemps = float(v[[key for key in v.keys() if key.endswith("_input")][0]])
            # sometimes, acpitz-acpi-0 is not available at all, but we can fallback on k10temp-pci-00c3
            elif self.readAttempts > 30:
                if "k10temp-pci-00c3" in sensorsOutput.keys():
                    cores += 1
                    sumCoreTemps = float(sensorsOutput["k10temp-pci-00c3"]["Tctl"]["temp1_input"])
                else:
                    print("Neither acpitz-acpi-0 or k10temp-pci-00c3 are available, please report this issue")
                    exit()
            else:
                self.readAttempts += 1
                return
        else:
            print("Unsupported cpu type: " + self.cpu_type)
            exit()

        measurement = sumCoreTemps / cores

        # if we're running on a 16 AND there's a discrete GPU, compare both temperature and take the highest
        if "16" in self.laptop_model:
            for k, v in sensorsOutput.items():
                if "junction" in v and "edge" in v:
                    dGpuTemp = v["edge"]["temp1_input"]
                    if dGpuTemp > measurement:
                        measurement = dGpuTemp

        self._tempIndex = (self._tempIndex + 1) % len(self.temps)
        self.temps[self._tempIndex] = measurement

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
        if debug:
            print(f"model: {self.laptop_model}, cpu_type: {self.cpu_type}, fan_count: {self.fan_count}")
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
