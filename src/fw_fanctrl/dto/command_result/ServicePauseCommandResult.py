from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class ServicePauseCommandResult(CommandResult):
    def __init__(self):
        super().__init__(CommandStatus.SUCCESS)

    def __str__(self):
        return "Service paused! The hardware fan control will take over"
