import collections
import sys
import threading
from time import sleep

from .Configuration import Configuration
from .exception.InvalidStrategyException import InvalidStrategyException
from .exception.JSONException import JSONException


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

        t = threading.Thread(
            target=self.socketController.startServerSocket,
            args=[self.commandManager],
        )
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
            return f"Strategy reset to default! Strategy in use: '{self.getCurrentStrategy().name}'"
        elif args.command == "use":
            try:
                self.overwriteStrategy(args.strategy)
                return f"Strategy in use: '{self.getCurrentStrategy().name}'"
            except InvalidStrategyException:
                raise InvalidStrategyException(f"The specified strategy is invalid: {args.strategy}")
        elif args.command == "reload":
            if self.configuration.reload():
                if self.overwrittenStrategy is not None:
                    self.overwriteStrategy(self.overwrittenStrategy.name)
            else:
                raise JSONException("Config file could not be parsed due to JSON Error")
            return f"Reloaded with success! Strategy in use: '{self.getCurrentStrategy().name}'"
        elif args.command == "pause":
            self.pause()
            return "Service paused! The hardware fan control will take over"
        elif args.command == "resume":
            self.resume()
            return f"Service resumed! Strategy in use: '{self.getCurrentStrategy().name}'"
        elif args.command == "print":
            if args.print_selection == "current":
                return self.getCurrentStrategy().name
            elif args.print_selection == "list":
                return "\n".join(self.configuration.getStrategies())
            elif args.print_selection == "speed":
                return str(self.speed) + "%"
        raise "Unknown command, unexpected."

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
            slope = (maxPoint["speed"] - minPoint["speed"]) / (maxPoint["temp"] - minPoint["temp"])
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
            print(
                f"[Error] > Missing strategy, exiting for safety reasons: {e.args[0]}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"[Error] > Critical error, exiting for safety reasons: {e}",
                file=sys.stderr,
            )
        exit(1)
