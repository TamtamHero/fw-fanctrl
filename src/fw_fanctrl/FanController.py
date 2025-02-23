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
from fw_fanctrl.dto.command_result.SetConfigurationCommandResult import SetConfigurationCommandResult
from fw_fanctrl.dto.command_result.StrategyChangeCommandResult import StrategyChangeCommandResult
from fw_fanctrl.dto.command_result.StrategyResetCommandResult import StrategyResetCommandResult
from fw_fanctrl.dto.runtime_result.RuntimeResult import RuntimeResult
from fw_fanctrl.dto.runtime_result.StatusRuntimeResult import StatusRuntimeResult
from fw_fanctrl.enum.CommandStatus import CommandStatus
from fw_fanctrl.exception.InvalidStrategyException import InvalidStrategyException
from fw_fanctrl.exception.UnknownCommandException import UnknownCommandException


class FanController:
    hardware_controller = None
    socket_controller = None
    configuration = None
    overwritten_strategy = None
    output_format = None
    speed = 0
    temp_history = collections.deque([0] * 100, maxlen=100)
    active = True
    timecount = 0

    def __init__(self, hardware_controller, socket_controller, config_path, strategy_name, output_format):
        self.hardware_controller = hardware_controller
        self.socket_controller = socket_controller
        self.configuration = Configuration(config_path)

        if strategy_name is not None and strategy_name != "":
            self.overwrite_strategy(strategy_name)

        self.output_format = output_format

        t = threading.Thread(
            target=self.socket_controller.start_server_socket,
            args=[self.command_manager],
        )
        t.daemon = True
        t.start()

    def get_actual_temperature(self):
        return self.hardware_controller.get_temperature()

    def set_speed(self, speed):
        self.speed = speed
        self.hardware_controller.set_speed(speed)

    def is_on_ac(self):
        return self.hardware_controller.is_on_ac()

    def pause(self):
        self.active = False
        self.hardware_controller.pause()

    def resume(self):
        self.active = True
        self.hardware_controller.resume()

    def overwrite_strategy(self, strategy_name):
        if strategy_name not in self.configuration.get_strategies():
            self.clear_overwritten_strategy()
            return
        self.overwritten_strategy = self.configuration.get_strategy(strategy_name)
        self.timecount = 0

    def clear_overwritten_strategy(self):
        self.overwritten_strategy = None
        self.timecount = 0

    def get_current_strategy(self):
        if self.overwritten_strategy is not None:
            return self.overwritten_strategy
        if self.is_on_ac():
            return self.configuration.get_default_strategy()
        return self.configuration.get_discharging_strategy()

    def command_manager(self, args):
        if args.command == "reset" or (args.command == "use" and args.strategy == "defaultStrategy"):
            self.clear_overwritten_strategy()
            return StrategyResetCommandResult(self.get_current_strategy().name, self.overwritten_strategy is None)
        elif args.command == "use":
            if args.strategy not in self.configuration.get_strategies():
                raise InvalidStrategyException(f"The specified strategy is invalid: {args.strategy}")
            self.overwrite_strategy(args.strategy)
            return StrategyChangeCommandResult(self.get_current_strategy().name, self.overwritten_strategy is None)
        elif args.command == "reload":
            self.configuration.reload()
            if self.overwritten_strategy is not None:
                self.overwrite_strategy(self.overwritten_strategy.name)
            return ConfigurationReloadCommandResult(self.get_current_strategy().name, self.overwritten_strategy is None)
        elif args.command == "pause":
            self.pause()
            return ServicePauseCommandResult()
        elif args.command == "resume":
            self.resume()
            return ServiceResumeCommandResult(self.get_current_strategy().name, self.overwritten_strategy is None)
        elif args.command == "print":
            if args.print_selection == "all":
                return self.dump_details()
            elif args.print_selection == "active":
                return PrintActiveCommandResult(self.active)
            elif args.print_selection == "current":
                return PrintCurrentStrategyCommandResult(
                    self.get_current_strategy().name, self.overwritten_strategy is None
                )
            elif args.print_selection == "list":
                return PrintStrategyListCommandResult(list(self.configuration.get_strategies()))
            elif args.print_selection == "speed":
                return PrintFanSpeedCommandResult(str(self.speed))
        elif args.command == "set_config":
            self.configuration.data = self.configuration.parse(args.provided_config)
            if self.overwritten_strategy is not None:
                self.overwrite_strategy(self.overwritten_strategy.name)
            self.configuration.save()
            return SetConfigurationCommandResult(
                self.get_current_strategy().name, vars(self.configuration), self.overwritten_strategy is None
            )
        raise UnknownCommandException(f"Unknown command: '{args.command}', unexpected.")

    # return mean temperature over a given time interval (in seconds)
    def get_moving_average_temperature(self, time_interval):
        sliced_temp_history = [x for x in self.temp_history if x > 0][-time_interval:]
        if len(sliced_temp_history) == 0:
            return self.get_actual_temperature()
        return float(round(sum(sliced_temp_history) / len(sliced_temp_history), 2))

    def get_effective_temperature(self, current_temp, time_interval):
        # the moving average temperature count for 2/3 of the effective temperature
        return float(round(min(self.get_moving_average_temperature(time_interval), current_temp), 2))

    def adapt_speed(self, current_temp):
        current_strategy = self.get_current_strategy()
        current_temp = self.get_effective_temperature(current_temp, current_strategy.moving_average_interval)
        min_point = current_strategy.speed_curve[0]
        max_point = current_strategy.speed_curve[-1]
        for e in current_strategy.speed_curve:
            if current_temp > e["temp"]:
                min_point = e
            else:
                max_point = e
                break

        if min_point == max_point:
            new_speed = min_point["speed"]
        else:
            slope = (max_point["speed"] - min_point["speed"]) / (max_point["temp"] - min_point["temp"])
            new_speed = int(min_point["speed"] + (current_temp - min_point["temp"]) * slope)
        if self.active:
            self.set_speed(new_speed)

    def dump_details(self):
        current_strategy = self.get_current_strategy()
        current_temperature = self.get_actual_temperature()
        moving_average_temp = self.get_moving_average_temperature(current_strategy.moving_average_interval)
        effective_temp = self.get_effective_temperature(current_temperature, current_strategy.moving_average_interval)

        return StatusRuntimeResult(
            current_strategy.name,
            self.overwritten_strategy is None,
            self.speed,
            current_temperature,
            moving_average_temp,
            effective_temp,
            self.active,
            vars(self.configuration),
        )

    def print_state(self):
        print(self.dump_details().to_output_format(self.output_format))

    def run(self, debug=True):
        try:
            while True:
                if self.active:
                    temp = self.get_actual_temperature()
                    # update fan speed every "fanSpeedUpdateFrequency" seconds
                    if self.timecount % self.get_current_strategy().fan_speed_update_frequency == 0:
                        self.adapt_speed(temp)
                        self.timecount = 0

                    self.temp_history.append(temp)

                    if debug:
                        self.print_state()
                    self.timecount += 1
                    sleep(1)
                else:
                    sleep(5)
        except InvalidStrategyException as e:
            _rte = RuntimeResult(CommandStatus.ERROR, f"Missing strategy, exiting for safety reasons: {e.args[0]}")
            print(_rte.to_output_format(self.output_format), file=sys.stderr)
        except Exception as e:
            _rte = RuntimeResult(CommandStatus.ERROR, f"Critical error, exiting for safety reasons: {e}")
            print(_rte.to_output_format(self.output_format), file=sys.stderr)
        exit(1)
