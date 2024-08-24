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
