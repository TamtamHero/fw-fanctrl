import os

from fw_fanctrl.dto.runtime_result.RuntimeResult import RuntimeResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class StatusRuntimeResult(RuntimeResult):
    def __init__(self, strategy, speed, temperature, movingAverageTemperature, effectiveTemperature, active):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy
        self.speed = speed
        self.temperature = temperature
        self.movingAverageTemperature = movingAverageTemperature
        self.effectiveTemperature = effectiveTemperature
        self.active = active

    def __str__(self):
        return f"Strategy: '{self.strategy}'{os.linesep}Speed: {self.speed}%{os.linesep}Temp: {self.temperature}°C{os.linesep}MovingAverageTemp: {self.movingAverageTemperature}°C{os.linesep}EffectiveTemp: {self.effectiveTemperature}°C{os.linesep}Active: {self.active}"
