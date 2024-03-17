# fw-fanctrl

This is a simple Python service for Linux that drives Framework Laptop's fan(s) speed according to a configurable speed/temp curve.
Its default configuration targets very silent fan operation, but it's easy to configure it for a different comfort/performance trade-off.
Its possible to specify two separate fan curves depending on whether the Laptop is charging/discharging.
Under the hood, it uses [fw-ectool](https://github.com/DHowett/fw-ectool) to change parameters in FrameWork's embedded controller (EC).

It is compatible with all kinds of 13" and 16" models, both AMD/Intel CPUs and with or without discrete GPU.

# Install

## Dependancies

This tool depends on `lm-sensors` to fetch CPU temperature:
```
sudo apt install lm-sensors
yes | sudo sensors-detect
```

To communicate with the embedded controller the `fw-ectool` is needed. You can either use the pre-compiled executable of `fw-ectool` in this repo, or recompile one from [this repo](https://github.com/DHowett/fw-ectool) and copy it in `./bin`.

Then run:
```
sudo ./install.sh
```

This bash script is going to create and enable a service that runs this repo's main script, `fanctrl.py`.
It will copy `fanctrl.py` (to an executable file `fw-fanctrl`) and `./bin/ectool` to `/usr/local/bin` and create a config file in `/home/<user>/.config/fw-fanctrl/config.json`

# Update

To install an update, you can just pull the latest commit on the `main` branch of this repository, and run the install script again.
It will overwrite the config file, so you might want to back it up if you have a custom one !

# Uninstall
```
sudo ./install.sh remove
```

# Configuration

There is a single `config.json` file where you can configure the service. You need to run the install script again after editing this config, or you can directly edit the installed config at `/home/<user>/.config/fw-fanctrl/config.json` and restart the service with:

```
sudo service fw-fanctrl restart
```

It contains different strategies, ranked from the most silent to the noisiest. It is possible to specify two different strategies for charging/discharging allowing for different optimization goals. On discharging one could have fan curve optimized for low fan speeds in order to save power while accepting a bit more heat. On charging one could have a fan curve that focuses on keeping the CPU from throttling and the system cool, at the expense of fan noise.
You can add new strategies, and if you think you have one that deserves to be shared, feel free to make a PR to this repo :)

Strategies can be configured with the following parameters:

- **SpeedCurve**:

    This is the curve points for `f(temperature) = fan speed`

    `fw-fanctrl` measures the CPU temperature, compute a moving average of it, and then find an appropriate `fan speed` value by interpolation on the curve.

- **FanSpeedUpdateFrequency**:

    Time interval between every update to the fan's speed. `fw-fanctrl` measures temperature every second and add it to its moving average, but the actual update to fan speed is made every 5s by default. This is for comfort, otherwise the speed is changed too often and it is noticeable and annoying, especially at low speed.
    For a more reactive fan, you can lower this setting.

- **MovingAverageInterval**:

    Number of seconds on which the moving average of temperature is computed. Increase it, and the fan speed will change more gradually. Lower it, and it will gain in reactivity. Defaults to 30 seconds.

## Charging/Discharging strategies

The strategy active by default is the one specified in the `defaultStrategy` entry. Optionally a separate strategy only active during discharge can be defined, using the `strategyOnDischarging` entry. By default no extra strategy for discharging is provided, the default stratgy is active during all times.
The charging status of the battery is fetched from the following file by default:
`/sys/class/power_supply/BAT1/status`
The default path can be overwritten by entering a value for `batteryChargingStatusPath` inside the `config.json` file.

# Misc

It is possible to hot swap the current strategy with another one by running the command
```
fw-fanctrl strategyName
```
where `strategyName is one of the strategies described in the config file.
