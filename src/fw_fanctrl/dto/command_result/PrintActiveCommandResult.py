from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class PrintActiveCommandResult(CommandResult):
    def __init__(self, active):
        super().__init__(CommandStatus.SUCCESS)
        self.active = active

    def __str__(self):
        return f"Active: {self.active}"
