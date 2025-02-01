from fw_fanctrl.dto.Printable import Printable
from fw_fanctrl.enum.CommandStatus import CommandStatus


class RuntimeResult(Printable):
    def __init__(self, status, reason="Unexpected"):
        super().__init__()
        self.status = status
        if status == CommandStatus.ERROR:
            self.reason = reason

    def __str__(self):
        return "Success!" if self.status == CommandStatus.SUCCESS else f"[Error] > An error occurred: {self.reason}"
