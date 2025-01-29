from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class StrategyResetCommandResult(CommandResult):
    def __init__(self, strategy):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy

    def __str__(self):
        return f"Strategy reset to default! Strategy in use: '{self.strategy}'"
