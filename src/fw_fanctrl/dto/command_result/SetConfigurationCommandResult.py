import json
import os

from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus


class SetConfigurationCommandResult(CommandResult):
    def __init__(self, strategy, default, configuration):
        super().__init__(CommandStatus.SUCCESS)
        self.strategy = strategy
        self.configuration = configuration
        self.default = default

    def __str__(self):
        return (
            f"Configuration updated with success: {json.dumps(self.configuration)}.{os.linesep}"
            f"Strategy in use: {self.strategy}{os.linesep}"
            f"Default: {self.default}"
        )
