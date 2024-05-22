# fw-fanctrl

This is a simple Python service for Linux that drives Framework Laptop's fan(s) speed according to a configurable speed/temp curve.
Its default configuration targets very silent fan operation, but it's easy to configure it for a different comfort/performance trade-off.
Its possible to specify two separate fan curves depending on whether the Laptop is charging/discharging.
Under the hood, it uses [ectool](https://gitlab.howett.net/DHowett/ectool) to change parameters in FrameWork's embedded controller (EC).

It is compatible with all kinds of 13" and 16" models, both AMD/Intel CPUs and with or without discrete GPU.

# Install

## Dependancies

To communicate with the embedded controller the `ectool` is required.
You can either use the precompiled executable of `ectool` in this repo or
disable its installation (`--no-ectool`) and add your own by recompiling it from [this repo](https://gitlab.howett.net/DHowett/ectool) and putting it in `[prefix-dir(/usr)]/bin`.

You also need to disable secure boot of your device for `ectool` to work (more details about why [here](https://www.howett.net/posts/2021-12-framework-ec/#using-fw-ectool))

Then run:
```
sudo ./install.sh
```

This bash script will to create and activate a service that runs this repo's main script, `fanctrl.py`.
It will copy `fanctrl.py` (to an executable file `fw-fanctrl`) and `./bin/ectool` to `[prefix-dir(/usr)]/bin` and create a config file
in `[sysconf-dir(/etc)]/fw-fanctrl/config.json`

this script also includes options to:
- specify an installation destination directory (`--dest-dir <installation destination directory (defaults to /usr)>`).
- specify an installation prefix directory (`--prefix-dir <installation prefix directory (defaults to /usr)>`).
- specify a default configuration directory (`--sysconf-dir <system configuration destination directory (defaults to /etc)>`).
- disable ectool installation and service activation (`--no-ectool`)
- disable post-install process (`--no-post-install`)

# Update

To install an update, you can pull the latest commit on the `main` branch of this repository, and run the install script again.

# Uninstall
```
sudo ./install.sh --remove
```

# Configuration

There is a single `config.json` file located at `[sysconf-dir(/etc)]/fw-fanctrl/config.json`.

(You will need to reload the configuration with)
```
fw-fanctrl --reload
```

It contains different strategies, ranked from the most silent to the noisiest. It is possible to specify two different strategies for charging/discharging allowing for different optimization goals.
On discharging one could have fan curve optimized for low fan speeds in order to save power while accepting a bit more heat. 
On charging one could have a fan curve that focuses on keeping the CPU from throttling and the system cool, at the expense of fan noise.
You can add new strategies, and if you think you have one that deserves to be shared, feel free to make a PR to this repo :)

Strategies can be configured with the following parameters:

- **SpeedCurve**:

    This is the curve points for `f(temperature) = fan speed`

    `fw-fanctrl` measures the CPU temperature, compute a moving average of it, and then find an appropriate `fan speed` value by interpolation on the curve.

- **FanSpeedUpdateFrequency**:

    Time interval between every update to the fan's speed. `fw-fanctrl` measures temperature every second and add it to its moving average, but the actual update to fan speed is controlled using this configuration. This is for comfort, otherwise the speed is changed too often and it is noticeable and annoying, especially at low speed.
    For a more reactive fan, you can lower this setting. **Defaults to 5 seconds.**

- **MovingAverageInterval**:

    Number of seconds on which the moving average of temperature is computed. Increase it, and the fan speed will change more gradually. Lower it, and it will gain in reactivity. **Defaults to 20 seconds.**

## Charging/Discharging strategies

The strategy active by default is the one specified in the `defaultStrategy` entry. Optionally a separate strategy only active during discharge can be defined, using the `strategyOnDischarging` entry. By default no extra strategy for discharging is provided, the default stratgy is active during all times.

# Commands

| option            | contexte        | description                     |
|-------------------|-----------------|---------------------------------|
| \<strategy>       | run & configure | the name of the strategy to use |
| --run             | run             | run the service                 |
| --config          | run             | specify the configuration path  |
| --no-log          | run             | disable state logging           |
| --query, -q       | configure       | print the current strategy name |
| --list-strategies | configure       | print the available strategies  |
| --reload, -r      | configure       | reload the configuration file   |
| --pause           | configure       | temporarily disable the service |
| --resume          | configure       | resume the service              |

