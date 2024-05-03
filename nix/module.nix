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
    # Install package
    environment.systemPackages = [
      package
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
        ExecStart = "${package}/bin/fw-fanctrl --config /etc/fw-fanctrl/config.json --no-log";
      };
      enable = true;
      wantedBy = [ "multi-user.target" ];
    };

    # Create suspend config
    environment.etc."systemd/system-sleep/fw-fanctrl-suspend.sh".source = pkgs.writeShellScript ''
        case \$1 in
          pre)  ${pkgs.util-linux}/bin/runuser -l $(${pkgs.coreutils}/bin/logname) -c "${package}/bin/fw-fanctrl sleep" ;;
          post) ${pkgs.util-linux}/bin/runuser -l $(${pkgs.coreutils}/bin/logname) -c "${package}/bin/fw-fanctrl defaultStrategy" ;;
        esac
      '';
  };
}
