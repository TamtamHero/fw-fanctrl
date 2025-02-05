import os

from fw_fanctrl.dto.runtime_result.RuntimeResult import RuntimeResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class StatusRuntimeResult(RuntimeResult):
    def __init__(
        self,
        strategy,
        default,
        speed,
        temperature,
        moving_average_temperature,
        effective_temperature,
        active,
        configuration,
    ):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy
        self.default = default
        self.speed = speed
        self.temperature = temperature
        self.movingAverageTemperature = moving_average_temperature
        self.effectiveTemperature = effective_temperature
        self.active = active
        self.configuration = configuration

    def __str__(self):
        return (
            f"Strategy: '{self.strategy}'{os.linesep}"
            f"Default: {self.default}{os.linesep}"
            f"Speed: {self.speed}%{os.linesep}"
            f"Temp: {self.temperature}°C{os.linesep}"
            f"MovingAverageTemp: {self.movingAverageTemperature}°C{os.linesep}"
            f"EffectiveTemp: {self.effectiveTemperature}°C{os.linesep}"
            f"Active: {self.active}{os.linesep}"
            f"DefaultStrategy: '{self.configuration["data"]["defaultStrategy"]}'{os.linesep}"
            f"DischargingStrategy: '{self.configuration["data"]["strategyOnDischarging"]}'{os.linesep}"
        )
