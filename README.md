# fw-fanctrl

[![Static Badge](https://img.shields.io/badge/Linux%2FGlobal-FCC624?style=flat&logo=linux&logoColor=FFFFFF&label=Platform&link=https%3A%2F%2Fgithub.com%2FTamtamHero%2Ffw-fanctrl%2Ftree%2Fmain)](https://github.com/TamtamHero/fw-fanctrl/tree/main)
![Static Badge](https://img.shields.io/badge/no%20binary%20blobs-30363D?style=flat&logo=GitHub-Sponsors&logoColor=4dff61)

[![Static Badge](https://img.shields.io/badge/Python__3.12-FFDE57?style=flat&label=Requirement&link=https%3A%2F%2Fwww.python.org%2Fdownloads)](https://www.python.org/downloads)

## Additional platforms:

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

## Documentation
Dokumentation can be found [here](./doc/README.md)
