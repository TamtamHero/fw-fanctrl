# Module and Package
For [NixOS](https://nixos.org/) this package (derivation) is in the offical [Nixpkgs](https://github.com/NixOS/nixpkgs/).
In addition we created a module to configure it via nix.

NixOS Search:
- [Module](https://search.nixos.org/options?channel=25.11&show=hardware.fw-fanctrl)
- [Package](https://search.nixos.org/packages?channel=25.11&show=fw-fanctrl)

# Installation
Here is an example how you could configure `fw-fanctrl`:

```nix
hardware.fw-fanctrl = {
  enable = true;                         # This is needed to enable the service
  config = {                             # This option is only needed if you want to add additional strategies
    defaultStrategy = "school";
    strategyOnDischarging = "laziest";   # Must not be set
    strategies = {
      "school" = {
        fanSpeedUpdateFrequency = 5;
        movingAverageInterval = 40;
        speedCurve = [
          { temp = 45; speed = 0; }
          { temp = 65; speed = 15; }
          { temp = 70; speed = 25; }
          { temp = 85; speed = 35; }
        ];
      };
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
  disableBatteryTempCheck = false;

};
```

This strategies gets appended to the [default config](https://github.com/TamtamHero/fw-fanctrl/blob/main/src/fw_fanctrl/_resources/config.json).

If you find any issue feel free to open an [Bug report | packaging/nix](https://github.com/TamtamHero/fw-fanctrl/issues)!
