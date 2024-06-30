# fw-fanctrl

This is a simple Python service for Linux that drives Framework Laptop's fan(s) speed according to a configurable speed/temp curve.
Its default configuration targets very silent fan operation, but it's easy to configure it for a different comfort/performance trade-off.
Its possible to specify two separate fan curves depending on whether the Laptop is charging/discharging.
Under the hood, it uses [ectool](https://gitlab.howett.net/DHowett/ectool) to change parameters in Framework's embedded controller (EC).

It is compatible with all kinds of 13" and 16" models, both AMD/Intel CPUs, with or without a discrete GPU.

# Install
For NixOS this repo contains an Flake. You could add it to your config like this:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    fw-fanctrl = {
      url = "github:TamtamHero/fw-fanctrl/packaging/nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs = {nixpkgs, fw-fanctrl}: {
    nixosConfigurations.foo = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
          fw-fanctrl.nixosModules.default
          configuration.nix
      ];
    };
  }
}
```
and then add in your *configuration.nix*:
```nix
# Enable fw-fanctrl
programs.fw-fanctrl.enable = true;

# Add a custom config
programs.fw-fanctrl.config = {
  defaultStrategy = "lazy";
  strategies = {
    "lazy" = {
      fanSpeedUpdateFrequency = 5;
      movingAverageInterval = 30;
      speedCurve = [
        { temp = 0; speed = 15; }
        { temp = 50; speed = 15; }
        { temp = 65; speed = 25; }
        { temp = 70; speed = 35; }
        { temp = 75; speed = 50; }
        { temp = 85; speed = 100; }
      ];
    };
  };
};

# Add a custom config from an existing JSON file
programs.fw-fanctrl.config = builtins.fromJSON (builtins.readFile ./config.json)

# Or just change the default strategy form the default config
programs.fw-fanctrl.config.defaultStrategy = "medium";
```

Non NixOS install is described [here](https://github.com/TamtamHero/fw-fanctrl/blob/main/README.md#Install)


# Configuration

The default config contains different strategies, ranked from the most silent to the noisiest. It is possible to specify two different strategies for charging/discharging allowing for different optimization goals.
On discharging one could have fan curve optimized for low fan speeds in order to save power while accepting a bit more heat. 
On charging one could have a fan curve that focuses on keeping the CPU from throttling and the system cool, at the expense of fan noise.
You can add new strategies, and if you think you have one that deserves to be shared, feel free to make a PR to this repo :)

Strategies can be configured with the following parameters:

- **SpeedCurve**:

    This is the curve points for `f(temperature) = fan speeds`

    `fw-fanctrl` measures the CPU temperature, compute a moving average of it, and then find an appropriate `fan speed` value by interpolation on the curve.

- **FanSpeedUpdateFrequency**:

    Time interval between every update to the fan's speed. `fw-fanctrl` measures temperature every second and add it to its moving average, but the actual update to fan speed is controlled using this configuration. This is for comfort, otherwise the speed is changed too often and it is noticeable and annoying, especially at low speed.
    For a more reactive fan, you can lower this setting. **Defaults to 5 seconds.**

- **MovingAverageInterval**:

    Number of seconds on which the moving average of temperature is computed. Increase it, and the fan speed will change more gradually. Lower it, and it will gain in reactivity. **Defaults to 20 seconds.**

## Charging/Discharging strategies

The strategy active by default is the one specified in the `defaultStrategy` entry. Optionally a separate strategy only active during discharge can be defined, using the `strategyOnDischarging` entry. By default no extra strategy for discharging is provided, the default strategy is active during all times.

# Commands

| Option            | Context         | Description                     |
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

