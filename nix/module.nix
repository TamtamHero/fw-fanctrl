{ options, config, lib, pkgs, stdenv, ... }:

with lib;
with lib.types;
let
  cfg = config.programs.fw-fanctrl;
  fw-fanctrl = pkgs.callPackage ./packages/fw-fanctrl.nix {};
  defaultConfig = builtins.fromJSON (builtins.readFile ../config.json);
in
{
  options.programs.fw-fanctrl = {
    enable = mkOption {
      type = bool;
      default = false;
      description = ''
        Enable fw-fanctrl systemd service and install the needed packages.
      '';
    };
    config = {
      defaultStrategy = mkOption {
        type = str;
        default = defaultConfig.defaultStrategy;
        description = "Default strategy to use";
      };
      strategyOnDischarging = mkOption {
        type = str;
        default = defaultConfig.strategyOnDischarging; 
        description = "Default strategy on discharging";
      };
      batteryChargingStatusPath = mkOption {
        type = str;
        default = "/sys/class/power_supply/BAT1/status";
        description = "";
      };
      strategies = mkOption {
        default = defaultConfig.strategies;
        type = attrsOf (submodule (
          { options, name, ... }:
          {
            options = {
              name = mkOption {
                type = str;
                default = "";
                description = "Name of the strategy";
              };
              fanSpeedUpdateFrequency = mkOption {
                type = int;
                default = 5;
                description = "How often the fan speed should be updated in seconds";
              };
              movingAverageInterval = mkOption {
                type = int;
                default = 25;
                description = "Interval (seconds) of the last temperatures to use to calculate the average temperature";
              };
              speedCurve = mkOption {
                default = [];
                description = "How should the speed curve look like";
                type = listOf (submodule (
                  { options, ... }:
                  {
                    options = {
                      temp = mkOption {
                        type = int;
                        default = 0;
                        description = "Temperature at which the fan speed should be changed";
                      };
                      speed = mkOption {
                        type = int;
                        default = 0;
                        description = "Percent how fast the fan should run at";
                      };
                    };
                  }
                ));
              }; 
            };
          }
        ));
      };
    };
  };

  config = mkIf cfg.enable {
    # Install package
    environment.systemPackages = with pkgs; [
      fw-fanctrl
      fw-ectool
    ];

    # Create config
    environment.etc."fw-fanctrl/config.json" = {
      text = builtins.toJSON cfg.config;
    };

    # Create Service
    systemd.services.fw-fanctrl = {
      description = "Framework Fan Controller";
      after = [ "multi-user.target" ];
      serviceConfig = {
        Type = "simple";
        Restart = "always";
        ExecStart = "${fw-fanctrl}/bin/fw-fanctrl --run --config /etc/fw-fanctrl/config.json --no-log";
        ExecStopPost = "${pkgs.fw-ectool}/bin/ectool autofanctrl";
      };
      enable = true;
      wantedBy = [ "multi-user.target" ];
    };

    # Create suspend config
    environment.etc."systemd/system-sleep/fw-fanctrl-suspend.sh".source = pkgs.writeShellScript "fw-fanctrl-suspend" (
      builtins.replaceStrings [ ''/usr/bin/python3 "%PREFIX_DIRECTORY%/bin/fw-fanctrl"'' "/bin/bash" ] [ "${fw-fanctrl}/bin/fw-fanctrl" "" ] (
        builtins.readFile ../services/system-sleep/fw-fanctrl-suspend
      )
    );
  };
}
