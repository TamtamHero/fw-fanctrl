{ options, config, lib, pkgs, ... }:

with lib;
with lib.types;
let
  cfg = config.programs.fw-fanctrl;
  fw-ectool = pkgs.callPackage ./packages/fw-ectool.nix {};
  fw-fanctrl = pkgs.callPackage ./packages/fw-fanctrl.nix {};
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
    # Install package
    environment.systemPackages = [
      fw-fanctrl
      fw-ectool
    ];

    # Create config
    environment.etc."fw-fanctrl/config.json" = {
      text = cfg.config;
    };

    # Create Service
    systemd.services.fw-fanctrl = {
      description = "Framework Fan Controller";
      after = [ "multi-user.target" ];
      serviceConfig = {
        Type = "simple";
        Restart = "always";
        ExecStart = "${fw-fanctrl}/bin/fw-fanctrl --config /etc/fw-fanctrl/config.json --no-log";
      };
      enable = true;
      wantedBy = [ "multi-user.target" ];
    };

    # Create suspend config
    environment.etc."systemd/system-sleep/fw-fanctrl-suspend.sh".source =
        pkgs.writeShellScript "fw-fanctrl-suspend.sh" (builtins.replaceStrings [ "runuser" "logname" "fw-fanctrl" ] [ "${pkgs.util-linux}/bin/runuser" "${pkgs.coreutils}/bin/logname" "${fw-fanctrl}/bin/fw-fanctrl" ] (builtins.readFile ../services/system-sleep/fw-fanctrl-suspend));
  };
}
