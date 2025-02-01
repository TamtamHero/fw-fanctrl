import os

from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class PrintStrategyListCommandResult(CommandResult):
    def __init__(self, strategies):
        super().__init__(CommandStatus.SUCCESS)
        self.strategies = strategies

    def __str__(self):
        printable_list = f"{os.linesep}- ".join(self.strategies)
        return f"Strategy list: {os.linesep}- {printable_list}"
