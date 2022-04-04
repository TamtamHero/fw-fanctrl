import argparse
import subprocess
from time import sleep
import json


class FanController:
    ## constants
    CORE_NUMBER = 4

    ## state
    speed = 0
    temps = [0] * 100
    _tempIndex = 0

    def __init__(self, configPath):
        with open(configPath, "r") as fp:
            config = json.load(fp)
            self.speedCurve = config["speedCurve"]
            self.fanSpeedUpdateFrequency = config["fanSpeedUpdateFrequency"]
            self.movingAverageInterval = config["movingAverageInterval"]
        self.setSpeed(self.speedCurve[0]["speed"])
        self.updateTemperature()
        self.temps = [self.temps[self._tempIndex]] * 100

    def setSpeed(self, speed):
        self.speed = speed
        bashCommand = f"ectool --interface=lpc fanduty {speed}"
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
                "sensors -j",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                executable="/bin/bash",
            ).stdout
        )
        for i in range(0, self.CORE_NUMBER):
            sumCoreTemps += float(
                sensorsOutput["coretemp-isa-0000"]["Core " + str(i)][
                    "temp" + str(i + 2) + "_input"
                ]
            )

        self._tempIndex = (self._tempIndex + 1) % len(self.temps)
        self.temps[self._tempIndex] = sumCoreTemps / self.CORE_NUMBER

    # return mean temperature over a given time interval (in seconds)
    def getMovingAverageTemperature(self, timeInterval):
        tempSum = 0
        for i in range(0, timeInterval):
            tempSum += self.temps[self._tempIndex - i]
        return tempSum / timeInterval

    def printState(self):
        print(
            f"speed: {self.speed}% temp: {self.temps[self._tempIndex]}°C movingAverage: {self.getMovingAverageTemperature(self.movingAverageInterval)}°C"
        )

    def run(self, debug=True):
        while True:
            self.updateTemperature()

            # update fan speed every "fanSpeedUpdateFrequency" seconds
            if self._tempIndex % self.fanSpeedUpdateFrequency == 0:
                self.adaptSpeed()

            if debug:
                self.printState()

            sleep(1)


def main():
    parser = argparse.ArgumentParser(description="Emulate Ledger Nano/Blue apps.")
    parser.add_argument(
        "--config", type=str, help="Path to config file", default="./config.json"
    )
    parser.add_argument(
        "--no-log", help="Print speed/temp/meanTemp to stdout", action="store_true"
    )
    args = parser.parse_args()

    fan = FanController(configPath=args.config)
    fan.run(debug=not args.no_log)


if __name__ == "__main__":
    main()
