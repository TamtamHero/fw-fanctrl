# fw-fanctrl

[![Static Badge](https://img.shields.io/badge/Linux%E2%80%AF%2F%E2%80%AFGlobal-FCC624?style=flat&logo=linux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fmain)](https://github.com/TamtamHero/fw-fanctrl/tree/main)
![Static Badge](https://img.shields.io/badge/no%20binary%20blobs-30363D?style=flat&logo=GitHub-Sponsors&logoColor=4dff61)

[![Static Badge](https://img.shields.io/badge/Python%203.12-FFDE57?style=flat&label=Requirement&link=https%3A%2F%2Fwww.python.org%2Fdownloads)](https://www.python.org/downloads)

## Platforms

[![Static Badge](https://img.shields.io/badge/Linux%E2%80%AF%2F%E2%80%AFGlobal-FCC624?style=flat&logo=linux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fmain)](https://github.com/TamtamHero/fw-fanctrl/tree/main)
[![Static Badge](https://img.shields.io/badge/NixOS-5277C3?style=flat&logo=nixos&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fpackaging%2Fnix)](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix/doc/nix-flake.md)

**Third-party**<br>

[![Static Badge](https://img.shields.io/badge/Arch%20Linux-1793D1?style=flat&logo=archlinux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Faur.archlinux.org%2Fpackages%2Ffw-fanctrl-git)](https://aur.archlinux.org/packages/fw-fanctrl-git)
[![Static Badge](https://img.shields.io/badge/Fedora-51A2DA?style=flat&logo=fedora&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2Ftulilirockz%2Ffw-fanctrl-rpm)](https://github.com/tulilirockz/fw-fanctrl-rpm)

_You are a package manager? Add your platform here!_

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
  * [Platforms](#platforms)
  * [Description](#description)
  * [Table of Content](#table-of-content)
  * [Third-party projects](#third-party-projects)
  * [Documentation](#documentation)
  * [Installation](#installation)
    * [Platforms](#platforms-1)
    * [Requirements](#requirements)
    * [Dependencies](#dependencies)
    * [Instructions](#instructions)
  * [Update](#update)
  * [Uninstall](#uninstall)
  * [Development Setup](#development-setup)
<!-- TOC -->

## Third-party projects

_Have some cool project to show? Add yours to the list!_

| Name                                                                                                              | Description                                                                                                         | Picture                                                                                                                                                                                                                   |
|-------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [fw&#8209;fanctrl&#8209;gui](https://github.com/leopoldhub/fw-fanctrl-gui)                                        | Simple customtkinter python gui with system tray for fw&#8209;fanctrl                                               | [<img src="https://github.com/leopoldhub/fw-fanctrl-gui/blob/master/doc/screenshots/tray.png?raw=true" width="200">](https://github.com/leopoldhub/fw-fanctrl-gui)                                                        |
| [fw-fanctrl-revived-gnome-shell-extension](https://github.com/ghostdevv/fw-fanctrl-revived-gnome-shell-extension) | A Gnome extension that provides a convenient way to control your framework laptop fan profile when using fw-fanctrl | [<img src="https://raw.githubusercontent.com/ghostdevv/fw-fanctrl-revived-gnome-shell-extension/refs/heads/main/.github/example.png" width="200">](https://github.com/ghostdevv/fw-fanctrl-revived-gnome-shell-extension) |

## Documentation

More documentation could be found [here](./doc/README.md).

## Installation

### Platforms

| Name&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Package&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Branch&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Documentation                                                                                                     |
|------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| Linux&nbsp;/&nbsp;Global                                                                                         | [installation&nbsp;script](https://github.com/TamtamHero/fw-fanctrl/blob/main/install.sh)                           | [main](https://github.com/TamtamHero/fw-fanctrl/tree/main)                                                         | [instructions](https://github.com/TamtamHero/fw-fanctrl/tree/main?tab=readme-ov-file#instructions)                |
| NixOS                                                                                                            | [flake](https://github.com/TamtamHero/fw-fanctrl/blob/packaging/nix/flake.nix)                                      | [packaging/nix](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix)                                       | [packaging/nix/doc/nix&#8209;flake](https://github.com/TamtamHero/fw-fanctrl/tree/packaging/nix/doc/nix-flake.md) |

**Third-party**

| Name&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Package&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Documentation                                                        |
|------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| Arch&nbsp;Linux                                                                                                  | [AUR](https://aur.archlinux.org/packages/fw-fanctrl-git)                                                            |                                                                      |
| Fedora&nbsp;/&nbsp;RPM                                                                                           | [COPR](https://copr.fedorainfracloud.org/coprs/tulilirockz/fw-fanctrl/package/fw-fanctrl/)                          | [GIT&nbsp;repository](https://github.com/tulilirockz/fw-fanctrl-rpm) |

### Requirements

| Name&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Version&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Url                                                                  |
|------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| Linux kernel                                                                                                     | \>= 6.11.x                                                                                                                |                                                                      |
| Python                                                                                                           | \>= 3.12.x                                                                                                                | [https://www.python.org/downloads](https://www.python.org/downloads) |

### Dependencies

Dependencies are downloaded and installed automatically, but can be excluded from the installation script if you wish to
do this manually.

| Name&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Version&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Url &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Sub&#8209;dependencies | Exclusion&nbsp;argument |
|------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|------------------------|-------------------------|
| DHowett@ectool                                                                                                   | build#899                                                                                                                 | [https://gitlab.howett.net/DHowett/ectool](https://gitlab.howett.net/DHowett/ectool)                             | libftdi                | `--no-ectool`           |

### Instructions

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

| argument                                                                        | description                                                    |
|---------------------------------------------------------------------------------|----------------------------------------------------------------|
| `--dest-dir <installation destination directory (defaults to /)>`               | specify an installation destination directory                  |
| `--prefix-dir <installation prefix directory (defaults to /usr)>`               | specify an installation prefix directory                       |
| `--sysconf-dir <system configuration destination directory (defaults to /etc)>` | specify a default configuration directory                      |
| `--no-ectool`                                                                   | disable ectool installation and service activation             |
| `--no-post-install`                                                             | disable post-install process                                   |
| `--no-pre-uninstall`                                                            | disable pre-uninstall process                                  |
| `--no-battery-sensors`                                                          | disable checking battery temperature sensors                   |
| `--no-pip-install`                                                              | disable the pip installation (should be done manually instead) |

## Update

To update, you can download or pull the appropriate branch from this repository, and run the installation script again.

## Uninstall

To uninstall, run the installation script with the `--remove` argument, as well as other
corresponding [arguments if necessary](#instructions)

```bash
sudo ./install.sh --remove
```

## Development Setup

> It is recommended to use a virtual environment to install development dependencies

Install the development dependencies with the following command:

```shell
pip install -e ".[dev]"
```

The project uses the [black](https://github.com/psf/black) formatter.

Please format your contributions before commiting them.

```shell
python -m black .
```
