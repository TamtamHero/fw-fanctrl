import re
import subprocess
from abc import ABC

from fw_fanctrl.hardwareController.HardwareController import HardwareController


class FrameworkToolHardwareController(HardwareController, ABC):

    def get_temperature(self):
        raw_out = subprocess.run(
            "framework_tool --thermal",
            stdout=subprocess.PIPE,
            shell=True,
            text=True,
        ).stdout
        raw_temps = re.findall(r":\s*(\d+)\sC", raw_out)
        temps = sorted([x for x in [int(x) for x in raw_temps] if x > 0], reverse=True)
        # safety fallback to avoid damaging hardware
        if len(temps) == 0:
            return 50
        return float(round(temps[0], 2))

    def set_speed(self, speed):
        subprocess.run(f"framework_tool --fansetduty {speed}", stdout=subprocess.PIPE, shell=True)

    def is_on_ac(self):
        raw_out = subprocess.run(
            "framework_tool --power",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=True,
            text=True,
        ).stdout
        return len(re.findall(r"AC\sis:\s*connected", raw_out)) > 0

    def pause(self):
        subprocess.run("framework_tool --autofanctrl", stdout=subprocess.PIPE, shell=True)

    def resume(self):
        # Empty for framework_tool, as setting an arbitrary speed disables the automatic fan control
        pass
