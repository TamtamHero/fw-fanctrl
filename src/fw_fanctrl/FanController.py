import collections
import sys
import threading
from time import sleep

from fw_fanctrl.Configuration import Configuration
from fw_fanctrl.dto.command_result.ConfigurationReloadCommandResult import ConfigurationReloadCommandResult
from fw_fanctrl.dto.command_result.PrintActiveCommandResult import PrintActiveCommandResult
from fw_fanctrl.dto.command_result.PrintCurrentStrategyCommandResult import PrintCurrentStrategyCommandResult
from fw_fanctrl.dto.command_result.PrintFanSpeedCommandResult import PrintFanSpeedCommandResult
from fw_fanctrl.dto.command_result.PrintStrategyListCommandResult import PrintStrategyListCommandResult
from fw_fanctrl.dto.command_result.ServicePauseCommandResult import ServicePauseCommandResult
from fw_fanctrl.dto.command_result.ServiceResumeCommandResult import ServiceResumeCommandResult
from fw_fanctrl.dto.command_result.StrategyChangeCommandResult import StrategyChangeCommandResult
from fw_fanctrl.dto.command_result.StrategyResetCommandResult import StrategyResetCommandResult
from fw_fanctrl.dto.runtime_result.RuntimeResult import RuntimeResult
from fw_fanctrl.dto.runtime_result.StatusRuntimeResult import StatusRuntimeResult
from fw_fanctrl.enum.CommandStatus import CommandStatus
from fw_fanctrl.exception.InvalidStrategyException import InvalidStrategyException
from fw_fanctrl.exception.JSONException import JSONException
from fw_fanctrl.exception.UnknownCommandException import UnknownCommandException


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
            slope = (maxPoint["speed"] - minPoint["speed"]) / (maxPoint["temp"] - minPoint["temp"])
            newSpeed = int(minPoint["speed"] + (currentTemp - minPoint["temp"]) * slope)
        if self.active:
            self.setSpeed(newSpeed)

    def dumpDetails(self):
        currentStrategy = self.getCurrentStrategy()
        currentTemperture = self.getActualTemperature()
        movingAverageTemp = self.getMovingAverageTemperature(currentStrategy.movingAverageInterval)
        effectiveTemp = self.getEffectiveTemperature(currentTemperture, currentStrategy.movingAverageInterval)

        return StatusRuntimeResult(
            currentStrategy.name, self.speed, currentTemperture, movingAverageTemp, effectiveTemp, self.active
        )

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
