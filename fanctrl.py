#! /usr/bin/python3

import argparse
from http.client import SWITCHING_PROTOCOLS
import subprocess
from time import sleep
import json


class FanController:
    # state
    speed = 0
    temps = [0] * 100
    _tempIndex = 0
    lastBatteryStatus = ""
    switchableFanCurve = False
    
    
    def __init__(self, configPath, strategy):
        with open(configPath, "r") as fp:
            config = json.load(fp)

        if strategy == "":
            strategyOnCharging = config["defaultStrategy"]  
        else:
            strategyOnCharging = strategy
        
        self.strategyOnCharging = config["strategies"][strategyOnCharging]
        # if the user didnt specify a separate strategy for discharging, use the same strategy as for charging
        strategyOnDischarging = config["strategyOnDischarging"]
        if strategyOnDischarging == "":
            self.switchableFanCurve = False
            self.strategyOnDischarging = self.strategyOnCharging
        else:
            self.strategyOnDischarging = config["strategies"][strategyOnDischarging]
            self.switchableFanCurve = True
            self.batteryChargingStatusPath = config["batteryChargingStatusPath"]
            if self.batteryChargingStatusPath == "":
                self.batteryChargingStatusPath = "/sys/class/power_supply/BAT1/status"

        #self.updateStrategy()
        self.speedCurve = self.strategyOnCharging["speedCurve"]
        self.fanSpeedUpdateFrequency = self.strategyOnCharging["fanSpeedUpdateFrequency"]
        self.movingAverageInterval = self.strategyOnCharging["movingAverageInterval"]
        self.setSpeed(self.speedCurve[0]["speed"])
        self.updateTemperature()
        self.temps = [self.temps[self._tempIndex]] * 100
        

    def updateStrategy(self):
        update = self.getBatteryChargingStatus()
        if update == 0:
            return      # if charging status unchanged do nothing
        elif update == 1:
            strategy = self.strategyOnCharging
        elif update == 2:
            strategy = self.strategyOnDischarging
        
        # load fan curve according to strategy
        self.speedCurve = strategy["speedCurve"]
        self.fanSpeedUpdateFrequency = strategy["fanSpeedUpdateFrequency"]
        self.movingAverageInterval = strategy["movingAverageInterval"]
        self.setSpeed(self.speedCurve[0]["speed"])
        self.updateTemperature()
        self.temps = [self.temps[self._tempIndex]] * 100

    
    def getBatteryChargingStatus(self):
        with open(self.batteryChargingStatusPath, "r") as fb:
            currentBatteryStatus = fb.readline().rstrip('\n')

            if currentBatteryStatus == self.lastBatteryStatus:
                return 0                # battery charging status hasnt change - dont switch fan curve
            elif currentBatteryStatus != self.lastBatteryStatus:
                self.lastBatteryStatus = currentBatteryStatus
                if currentBatteryStatus == "Charging":
                    return 1
                elif currentBatteryStatus == "Discharging":
                    return 2


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
            f"speed: {self.speed}% temp: {self.temps[self._tempIndex]}°C movingAverage: {round(self.getMovingAverageTemperature(self.movingAverageInterval), 2)}°C"
        )

    def run(self, debug=True):
        while True:
            if self.switchableFanCurve:
                self.updateStrategy()
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
        "--no-log", help="Print speed/meanTemp to stdout", action="store_true"
    )
    args = parser.parse_args()

    fan = FanController(configPath=args.config, strategy=args.strategy)
    fan.run(debug=not args.no_log)


if __name__ == "__main__":
    main()
