{ options, config, lib, pkgs, ... }:

with lib;
with lib.types;
let
  cfg = config.programs.fw-fanctrl;
  package = pkgs.callPackage ./package.nix {};
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
    config = mkOption {
      type = lines;
      default = builtins.readFile ../config.json;
      description = ''
        Config json that creates the config in /etc/fw-fanctrl/config.json.
      '';
    };
  };

  config = mkIf cfg.enable {
    environment.systemPackages = [
      package
    ];

    environment.etc."fw-fanctrl/config.json" = {
      text = cfg.config;
    };

    systemd.services.fw-fanctrl = {
      description = "Framework Fan Controller";
      after = "multi-user.target";
      type = "simple";
      unitConfig = ''
        Type=simple
        Restart=always
      '';
      script = "${package}/bin/fw-fanctrl --config /etc/fw-fanctrl/config.json --no-log";
      enable = true;
      wantedBy = "multi-user.target";
    };
  };
}
