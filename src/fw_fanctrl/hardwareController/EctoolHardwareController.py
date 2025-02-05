import re
import subprocess
from abc import ABC

from fw_fanctrl.hardwareController.HardwareController import HardwareController


class EctoolHardwareController(HardwareController, ABC):
    noBatterySensorMode = False
    nonBatterySensors = None

    def __init__(self, no_battery_sensor_mode=False):
        if no_battery_sensor_mode:
            self.noBatterySensorMode = True
            self.populate_non_battery_sensors()

    def populate_non_battery_sensors(self):
        self.nonBatterySensors = []
        raw_out = subprocess.run(
            "ectool tempsinfo all",
            stdout=subprocess.PIPE,
            shell=True,
            text=True,
        ).stdout
        battery_sensors_raw = re.findall(r"\d+ Battery", raw_out, re.MULTILINE)
        battery_sensors = [x.split(" ")[0] for x in battery_sensors_raw]
        for x in re.findall(r"^\d+", raw_out, re.MULTILINE):
            if x not in battery_sensors:
                self.nonBatterySensors.append(x)

    def get_temperature(self):
        if self.noBatterySensorMode:
            raw_out = "".join(
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
            raw_out = subprocess.run(
                "ectool temps all",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
            ).stdout
        raw_temps = re.findall(r"\(= (\d+) C\)", raw_out)
        temps = sorted([x for x in [int(x) for x in raw_temps] if x > 0], reverse=True)
        # safety fallback to avoid damaging hardware
        if len(temps) == 0:
            return 50
        return float(round(temps[0], 1))

    def set_speed(self, speed):
        subprocess.run(f"ectool fanduty {speed}", stdout=subprocess.PIPE, shell=True)

    def is_on_ac(self):
        raw_out = subprocess.run(
            "ectool battery",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=True,
            text=True,
        ).stdout
        return len(re.findall(r"Flags.*(AC_PRESENT)", raw_out)) > 0

    def pause(self):
        subprocess.run("ectool autofanctrl", stdout=subprocess.PIPE, shell=True)

    def resume(self):
        # Empty for ectool, as setting an arbitrary speed disables the automatic fan control
        pass
