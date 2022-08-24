import argparse
import subprocess
from time import sleep
import json


class FanController:
    # state
    speed = 0
    temps = [0] * 100
    _tempIndex = 0

    def __init__(self, configPath, strategy):
        with open(configPath, "r") as fp:
            config = json.load(fp)
        if strategy == "":
            strategy = config["defaultStrategy"]
        strategy = config["strategies"][strategy]
        self.speedCurve = strategy["speedCurve"]
        self.fanSpeedUpdateFrequency = strategy["fanSpeedUpdateFrequency"]
        self.movingAverageInterval = strategy["movingAverageInterval"]
        self.setSpeed(self.speedCurve[0]["speed"])
        self.updateTemperature()
        self.temps = [self.temps[self._tempIndex]] * 100

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
                "sensors -j",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                executable="/bin/bash",
            ).stdout
        )
        cores = 0
        for k, v in sensorsOutput["coretemp-isa-0000"].items():
            if k.startswith("Core "):
                i = int(k.split(" ")[1])
                cores += 1
                sumCoreTemps += float(v["temp" + str(i + 2) + "_input"])

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
    parser = argparse.ArgumentParser(
        description="Control Framework's laptop fan with a speed curve"
    )
    parser.add_argument(
        "--config", type=str, help="Path to config file", default="./config.json"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        help='Name of the strategy to use e.g: "lazy" (check config.json for others)',
        default="",
    )
    parser.add_argument(
        "--no-log", help="Print speed/temp/meanTemp to stdout", action="store_true"
    )
    args = parser.parse_args()

    fan = FanController(configPath=args.config, strategy=args.strategy)
    fan.run(debug=not args.no_log)


if __name__ == "__main__":
    main()
