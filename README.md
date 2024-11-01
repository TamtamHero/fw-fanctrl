# fw-fanctrl

[![Static Badge](https://img.shields.io/badge/Windows-0078D6?style=flat&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fpackaging%2Fwindows)](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/windows)

[![Static Badge](https://img.shields.io/badge/Python__3.12-FFDE57?style=flat&label=Requirement&link=https%3A%2F%2Fwww.python.org%2Fdownloads)](https://www.python.org/downloads)

## Additional platforms:

[![Static Badge](https://img.shields.io/badge/Linux%2FGlobal-FCC624?style=flat&logo=linux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fmain)](https://github.com/TamtamHero/fw-fanctrl/tree/main)

[![Static Badge](https://img.shields.io/badge/NixOS-5277C3?style=flat&logo=nixos&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fpackaging%2Fnix)](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix/doc/nix-flake.md)

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

## Table of Content

<!-- TOC -->
* [fw-fanctrl](#fw-fanctrl)
  * [Additional platforms:](#additional-platforms)
  * [Description](#description)
  * [Table of Content](#table-of-content)
  * [Documentation](#documentation)
  * [Installation](#installation)
    * [Other Platforms](#other-platforms)
    * [Requirements](#requirements)
    * [Dependencies](#dependencies)
    * [Instructions](#instructions)
  * [Update](#update)
  * [Uninstall](#uninstall)
<!-- TOC -->

## Documentation

More documentation could be found [here](./doc/README.md).

## Installation

### Other Platforms

| name         | branch                                                                       | documentation                                                                                               |
|--------------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| Linux/Global | [main](https://github.com/TamtamHero/fw-fanctrl/tree/main)                   | [main/doc](https://github.com/TamtamHero/fw-fanctrl/tree/main/doc/README.md)                                |
| NixOS        | [packaging/nix](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix) | [packaging/nix/doc/nix-flake](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix/doc/nix-flake.md) |

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

Please note that the windows version of this service uses an unsigned
experimental [crosec](https://github.com/DHowett/FrameworkWindowsUtils) driver that may be unstable.
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

[Download the repo](https://github.com/TamtamHero/fw-fanctrl/archive/refs/heads/packaging/windows.zip) and extract it
manually, or download/clone it with the appropriate tools:

```shell
git clone --branch "packaging/windows" "https://github.com/TamtamHero/fw-fanctrl.git"
```

```shell
curl -L "https://github.com/TamtamHero/fw-fanctrl/archive/refs/heads/packaging/windows.zip" -o "./fw-fanctrl.zip" && tar -xf "./fw-fanctrl.zip" && del "./fw-fanctrl.zip"
```

Then run the installation script with administrator privileges (by double clicking it, or with the following command)

```shell
install.bat
```

You can add a number of arguments to the installation command to suit your needs

| argument              | description                                  |
|-----------------------|----------------------------------------------|
| `/no-battery-sensors` | disable checking battery temperature sensors |

## Update

To update, you can download or pull the appropriate branch from this repository, and run the installation script again.

## Uninstall

To uninstall, run the uninstallation script `uninstall.bat` (by double clicking it, or with the following command)

```shell
uninstall.bat
```
