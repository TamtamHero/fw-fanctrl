import json

from fw_fanctrl.Strategy import Strategy
from fw_fanctrl.exception.InvalidStrategyException import InvalidStrategyException


class Configuration:
    path = None
    data = None

    def __init__(self, path):
        self.path = path
        self.reload()

    def reload(self):
        with open(self.path, "r") as fp:
            try:
                self.data = json.load(fp)
            except json.JSONDecodeError:
                return False
        return True

    def get_strategies(self):
        return self.data["strategies"].keys()

    def get_strategy(self, strategy_name):
        if strategy_name == "strategyOnDischarging":
            strategy_name = self.data[strategy_name]
            if strategy_name == "":
                strategy_name = "defaultStrategy"
        if strategy_name == "defaultStrategy":
            strategy_name = self.data[strategy_name]
        if strategy_name is None or strategy_name not in self.data["strategies"]:
            raise InvalidStrategyException(strategy_name)
        return Strategy(strategy_name, self.data["strategies"][strategy_name])

    def get_default_strategy(self):
        return self.get_strategy("defaultStrategy")

    def get_discharging_strategy(self):
        return self.get_strategy("strategyOnDischarging")
