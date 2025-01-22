import re
import subprocess
from abc import ABC

from fw_fanctrl.hardwareController.HardwareController import HardwareController


class EctoolHardwareController(HardwareController, ABC):
    noBatterySensorMode = False
    nonBatterySensors = None

    def __init__(self, noBatterySensorMode=False):
        if noBatterySensorMode:
            self.noBatterySensorMode = True
            self.populateNonBatterySensors()

    def populateNonBatterySensors(self):
        self.nonBatterySensors = []
        rawOut = subprocess.run(
            "ectool tempsinfo all",
            stdout=subprocess.PIPE,
            shell=True,
            text=True,
        ).stdout
        batterySensorsRaw = re.findall(r"\d+ Battery", rawOut, re.MULTILINE)
        batterySensors = [x.split(" ")[0] for x in batterySensorsRaw]
        for x in re.findall(r"^\d+", rawOut, re.MULTILINE):
            if x not in batterySensors:
                self.nonBatterySensors.append(x)

    def getTemperature(self):
        if self.noBatterySensorMode:
            rawOut = "".join(
                [
                    subprocess.run(
                        "ectool temps " + x,
                        stdout=subprocess.PIPE,
                        shell=True,
                        text=True,
                    ).stdout
                    for x in self.nonBatterySensors
                ]
            )
        else:
            rawOut = subprocess.run(
                "ectool temps all",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
            ).stdout
        rawTemps = re.findall(r"\(= (\d+) C\)", rawOut)
        temps = sorted([x for x in [int(x) for x in rawTemps] if x > 0], reverse=True)
        # safety fallback to avoid damaging hardware
        if len(temps) == 0:
            return 50
        return round(temps[0], 1)

    def setSpeed(self, speed):
        subprocess.run(f"ectool fanduty {speed}", stdout=subprocess.PIPE, shell=True)

    def isOnAC(self):
        rawOut = subprocess.run(
            "ectool battery",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=True,
            text=True,
        ).stdout
        return len(re.findall(r"Flags.*(AC_PRESENT)", rawOut)) > 0

    def pause(self):
        subprocess.run("ectool autofanctrl", stdout=subprocess.PIPE, shell=True)

    def resume(self):
        pass
