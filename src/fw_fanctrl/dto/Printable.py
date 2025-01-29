import json

from fw_fanctrl.enum.OutputFormat import OutputFormat


class Printable:
    def __init__(self):
        super().__init__()

    def toOutputFormat(self, outputFormat):
        if outputFormat == OutputFormat.JSON:
            return json.dumps(self.__dict__)
        else:
            return str(self)
