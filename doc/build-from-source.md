# Installation

## Requirements

| name   | version | url                                                                  |
|--------|---------|----------------------------------------------------------------------|
| Python | 3.12.x  | [https://www.python.org/downloads](https://www.python.org/downloads) |

## Dependencies

Dependencies are downloaded and installed automatically, but can be excluded from the installation script if you wish to
do this manually.

| name           | version   | url                                                                                  | sub-dependencies | exclusion argument |
|----------------|-----------|--------------------------------------------------------------------------------------|------------------|--------------------|
| DHowett@ectool | build#899 | [https://gitlab.howett.net/DHowett/ectool](https://gitlab.howett.net/DHowett/ectool) | libftdi          | `--no-ectool`      |

## Instructions

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

# Update

To update, you can download or pull the appropriate branch from this repository, and run the installation script again.

# Uninstall

To uninstall, run the installation script with the `--remove` argument, as well as other
corresponding [arguments if necessary](#instructions)

```bash
sudo ./install.sh --remove
```

