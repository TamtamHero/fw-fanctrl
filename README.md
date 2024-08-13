# fw-fanctrl

[![Static Badge](https://img.shields.io/badge/Windows-0078D6?style=flat&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fpackaging%2Fwindows)](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/windows)

[![Static Badge](https://img.shields.io/badge/Python__3.12-FFDE57?style=flat&label=Requirement&link=https%3A%2F%2Fwww.python.org%2Fdownloads)](https://www.python.org/downloads)

## Additional platforms:

[![Static Badge](https://img.shields.io/badge/Linux%2FGlobal-FCC624?style=flat&logo=linux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fmain)](https://github.com/TamtamHero/fw-fanctrl/tree/main)

[![Static Badge](https://img.shields.io/badge/NixOS-5277C3?style=flat&logo=nixos&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fpackaging%2Fnix)](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix)

## Description

Fw-fanctrl is a simple Python CLI service that controls Framework Laptop's fan(s)
speed according to a configurable speed/temperature curve.

Its default strategy aims for very quiet fan operation, but you can choose amongst the other provided strategies, or
easily configure your own for a different comfort/performance trade-off.

It also is possible to assign separate strategies depending on whether the laptop is charging or discharging.

Under the hood, it uses [ectool](https://gitlab.howett.net/DHowett/ectool)
to change parameters in Framework's embedded controller (EC).

It is compatible with all 13" and 16" models, both AMD/Intel CPUs, with or without a discrete GPU.

If the service is paused or stopped, the fans will revert to their default behaviour.

## Installation

### Requirements

| name   | version | url                                                                  |
|--------|---------|----------------------------------------------------------------------|
| Python | 3.12.x  | [https://www.python.org/downloads](https://www.python.org/downloads) |

### Dependencies

Dependencies are downloaded and installed automatically.

| name           | version      | url                                                                                                  |
|----------------|--------------|------------------------------------------------------------------------------------------------------|
| DHowett@crosec | v0.0.2       | [https://github.com/DHowett/FrameworkWindowsUtils](https://github.com/DHowett/FrameworkWindowsUtils) |
| DHowett@ectool | artifact#904 | [https://gitlab.howett.net/DHowett/ectool](https://gitlab.howett.net/DHowett/ectool)                 |
| nssm           | 2.24         | [https://nssm.cc](https://nssm.cc)                                                                   |

### Instructions

Please note that the windows version of this service uses an unsigned experimental [crosec](https://github.com/DHowett/FrameworkWindowsUtils) driver that may be unstable.
We are not responsible for any damage or data loss that this may cause.

First, make sure that you have disabled secure boot in your BIOS/UEFI settings.
(more details on why [here](https://www.howett.net/posts/2021-12-framework-ec/#using-fw-ectool))

```
============================================================================
IF YOU HAVE BITLOCKER ENABLED, YOU WILL NEED YOUR RECOVERY CODE ON BOOT !!!!
PLEASE MAKE A BACKUP OF YOUR BITLOCKER RECOVERY KEY BEFORE YOU DO ANYTHING !
YOU GET LOCKED OUT OF YOUR COMPUTER IF YOU ARE NOT CAREFUL ENOUGH !
============================================================================
```

[Download the repo](https://github.com/TamtamHero/fw-fanctrl/archive/refs/heads/packaging/windows.zip) and extract it manually, or
download/clone it with the appropriate tools:

```shell
git clone --branch "packaging/windows" "https://github.com/TamtamHero/fw-fanctrl.git"
```

```shell
curl -L "https://github.com/TamtamHero/fw-fanctrl/archive/refs/heads/packaging/windows.zip" -o "./fw-fanctrl.zip" && unzip "./fw-fanctrl.zip" -d "./fw-fanctrl" && rm -rf "./fw-fanctrl.zip"
```

Then run the installation script with administrator privileges (by double clicking it, or with the following command)

```shell
install.bat
```

## Update

To update, you can download or pull the appropriate branch from this repository, and run the installation script again.

## Uninstall

To uninstall, run the uninstallation script `uninstall.bat` (by double clicking it, or with the following command)

```shell
uninstall.bat
```

## Configuration

After installation, you will find the configuration file in the following location:

`%Appdata%\fw-fanctrl\config.json`

It contains a list of strategies, ranked from the quietest to loudest, as well as the default and discharging
strategies.

For example, one could use a lower fan speed strategy on discharging to optimise battery life (- noise, + heat),
and a high fan speed strategy on AC (+ noise, - heat).

You can add or edit strategies, and if you think you have one that deserves to be shared, feel free to make a PR to this
repo :)

### Default strategy

The default strategy is the one used when the service is started.

It can be changed by replacing the value of the `defaultStrategy` field with one of the strategies present in the
configuration.

```json
"defaultStrategy": "[STRATEGY NAME]"
```

### Charging/Discharging strategies

The discharging strategy is the one that will be used when the laptop is not on AC,
Otherwise the default strategy is used.

It can be changed by replacing the value of the `strategyOnDischarging` field with one of the strategies present in the
configuration.

```json
"strategyOnDischarging": "[STRATEGY NAME]"
```

This is optional and can be left empty to have the same strategy at all times.

### Editing strategies

Strategies can be configured with the following parameters:

> **SpeedCurve**:
>
> It is represented by the curve points for `f(temperature) = fan(s) speed`.
>
> ```json
> "speedCurve": [
>     { "temp": [TEMPERATURE POINT], "speed": [PERCENTAGE SPEED] },
>     ...
> ]
> ```
>
> `fw-fanctrl` measures the CPU temperature, calculates a moving average of it, and then finds an
> appropriate `fan speed`
> value by interpolating on the curve.

> **FanSpeedUpdateFrequency**:
>
> It is the interval in seconds between fan speed calculations.
>
> ```json
> "fanSpeedUpdateFrequency": [UPDATE FREQUENCY]
> ```
>
> This is for comfort, otherwise the speed will change too often, which is noticeable and annoying, especially at low
> speed.
>
> For a more responsive fan, you can reduce this setting.
>
> **Defaults to 5 seconds.** (minimum 1)

> **MovingAverageInterval**:
>
> It is the number of seconds over which the moving average of temperature is calculated.
>
> ```json
> "movingAverageInterval": [AVERAGING INTERVAL]
> ```
>
> Increase it, and the fan speed changes more gradually. Lower it, and it becomes more responsive.
>
> **Defaults to 20 seconds.** (minimum 1)

---

Once the configuration has been changed, you must reload it with the following command

```bash
fw-fanctrl --reload
```

## Commands

Here is a list of commands and options used to interact with the service.

the base of all commands is the following

```shell
fw-fanctrl [commands and options]
```

First, the global options

| Option                    | Optional | choices | Default | Description                                                                    |
|---------------------------|----------|---------|---------|--------------------------------------------------------------------------------|
| --socket-controller, --sc | yes      | win32   | win32   | the socket controller to use for communication between the cli and the service |

**run**

run the service manually

If you have installed it correctly, the systemd `fw-fanctrl.service` service will do this for you, so you probably will
never need those.

| Option                      | Optional | choices        | Default              | Description                                                                       |
|-----------------------------|----------|----------------|----------------------|-----------------------------------------------------------------------------------|
| \<strategy>                 | yes      |                | the default strategy | the name of the strategy to use                                                   |
| --config                    | yes      | \[CONFIG_PATH] |                      | the configuration file path                                                       |
| --silent, -s                | yes      |                |                      | disable printing speed/temp status to stdout                                      |
| --hardware-controller, --hc | yes      | ectool         | ectool               | the hardware controller to use for fetching and setting the temp and fan(s) speed |

**use**

change the current strategy

| Option      | Optional | Description                     |
|-------------|----------|---------------------------------|
| \<strategy> | no       | the name of the strategy to use |

**reset**

reset to the default strategy

**reload**

reload the configuration file

**pause**

pause the service

**resume**

resume the service

**print**

print the selected information

| Option             | Optional | choices       | Default | Description            |
|--------------------|----------|---------------|---------|------------------------|
| \<print_selection> | yes      | current, list | current | what should be printed |