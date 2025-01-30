from enum import Enum


class CommandStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
