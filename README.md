# fw-fanctrl

[![Static Badge](https://img.shields.io/badge/Linux%2FGlobal-FCC624?style=flat&logo=linux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fmain)](https://github.com/TamtamHero/fw-fanctrl/tree/main)
![Static Badge](https://img.shields.io/badge/no%20binary%20blobs-30363D?style=flat&logo=GitHub-Sponsors&logoColor=4dff61)

[![Static Badge](https://img.shields.io/badge/Python__3.12-FFDE57?style=flat&label=Requirement&link=https%3A%2F%2Fwww.python.org%2Fdownloads)](https://www.python.org/downloads)

## Additional platforms:

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
| name  | branch        | documentation |
|-------|---------------|---------------|
| NixOS | [packaging/nix](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix) | [packaging/nix/doc/nix-flake](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix/doc/nix-flake.md) |

### Requirements

| name   | version | url                                                                  |
|--------|---------|----------------------------------------------------------------------|
| Python | 3.12.x  | [https://www.python.org/downloads](https://www.python.org/downloads) |

### Dependencies

Dependencies are downloaded and installed automatically, but can be excluded from the installation script if you wish to
do this manually.

| name           | version   | url                                                                                  | sub-dependencies | exclusion argument |
|----------------|-----------|--------------------------------------------------------------------------------------|------------------|--------------------|
| DHowett@ectool | build#899 | [https://gitlab.howett.net/DHowett/ectool](https://gitlab.howett.net/DHowett/ectool) | libftdi          | `--no-ectool`      |

### Instructions

First, make sure that you have disabled secure boot in your BIOS/UEFI settings.
(more details on why [here](https://www.howett.net/posts/2021-12-framework-ec/#using-fw-ectool))

[Download the repo](https://github.com/TamtamHero/fw-fanctrl/archive/refs/heads/main.zip) and extract it manually, or
download/clone it with the appropriate tools:

```shell
git clone "https://github.com/TamtamHero/fw-fanctrl.git"
```

```shell
curl -L "https://github.com/TamtamHero/fw-fanctrl/archive/refs/heads/main.zip" -o "./fw-fanctrl.zip" && unzip "./fw-fanctrl.zip" -d "./fw-fanctrl" && rm -rf "./fw-fanctrl.zip"
```

Then run the installation script with administrator privileges

```bash
sudo ./install.sh
```

You can add a number of arguments to the installation command to suit your needs

| argument                                                                        | description                                        |
|---------------------------------------------------------------------------------|----------------------------------------------------|
| `--dest-dir <installation destination directory (defaults to /)>`               | specify an installation destination directory      |
| `--prefix-dir <installation prefix directory (defaults to /usr)>`               | specify an installation prefix directory           |
| `--sysconf-dir <system configuration destination directory (defaults to /etc)>` | specify a default configuration directory          |
| `--no-ectool`                                                                   | disable ectool installation and service activation |
| `--no-post-install`                                                             | disable post-install process                       |
| `--no-pre-uninstall`                                                            | disable pre-uninstall process                      |
| `--no-battery-sensors`                                                          | disable checking battery temperature sensors       |

## Update

To update, you can download or pull the appropriate branch from this repository, and run the installation script again.

## Uninstall

To uninstall, run the installation script with the `--remove` argument, as well as other
corresponding [arguments if necessary](#instructions)

```bash
sudo ./install.sh --remove
```

