from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class PrintFanSpeedCommandResult(CommandResult):
    def __init__(self, speed):
        super().__init__(CommandStatus.SUCCESS)
        self.speed = speed

    def __str__(self):
        return f"Current fan speed: '{self.speed}%'"
