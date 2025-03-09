import importlib.resources
import os

INTERNAL_RESOURCES_PATH = importlib.resources.files("fw_fanctrl").joinpath("_resources")

DEFAULT_CONFIGURATION_FILE_PATH = "/etc/fw-fanctrl/config.json"
SOCKETS_FOLDER_PATH = "/run/fw-fanctrl"
COMMANDS_SOCKET_FILE_PATH = os.path.join(SOCKETS_FOLDER_PATH, ".fw-fanctrl.commands.sock")
