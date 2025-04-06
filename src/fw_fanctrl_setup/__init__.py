import importlib.resources

MAIN_INTERNAL_RESOURCES_PATH = importlib.resources.files("fw_fanctrl").joinpath("_resources")
SETUP_INTERNAL_RESOURCES_PATH = importlib.resources.files("fw_fanctrl_setup").joinpath("_resources")
