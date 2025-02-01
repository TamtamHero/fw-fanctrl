from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class ServiceResumeCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Service resumed! Strategy in use: '{self.strategy}'"
