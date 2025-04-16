import os
import pathlib
import shlex
import sys

from fw_fanctrl_setup.CommandParser import CommandParser
from fw_fanctrl_setup.cleanup import cleanup
from fw_fanctrl_setup.configs import install_configs, uninstall_configs
from fw_fanctrl_setup.ectool import install_ectool, ectool_auto_behaviour, uninstall_ectool
from fw_fanctrl_setup.services import install_services, start_services, stop_services, uninstall_services


def uninstall(args, updating=False):
    if not args.no_pre_uninstall:
        stop_services()
    uninstall_services(str(pathlib.Path(args.dest_dir).joinpath(args.prefix_dir).joinpath("lib").joinpath("systemd")))
    if args.keep_config:
        print("Keeping configuration files")
    else:
        uninstall_configs(str(pathlib.Path(args.dest_dir).joinpath(args.sysconf_dir).joinpath("fw-fanctrl")))
    ectool_auto_behaviour(
        str(pathlib.Path(args.dest_dir).joinpath(args.prefix_dir).joinpath("bin").joinpath("ectool")),
        not updating or not args.no_post_install,
    )
    if args.no_ectool:
        print("Skipping `ectool` uninstallation")
    else:
        uninstall_ectool(str(pathlib.Path(args.dest_dir).joinpath(args.prefix_dir).joinpath("bin").joinpath("ectool")))
    cleanup()


def main():
    args = CommandParser().parse_args(shlex.split(shlex.join(sys.argv[1:])))
    print(args)

    if os.geteuid() != 0 and not args.no_sudo:
        print(
            "You must have root privileges to run this command, or disable the requirement with the `--no-sudo` argument.",
            file=sys.stderr,
        )
        exit(1)

    if args.remove:
        uninstall(args)
    else:
        print("Uninstalling older version...")
        uninstall(args, True)
        if args.no_ectool:
            print("Skipping `ectool` installation")
        else:
            install_ectool(
                str(pathlib.Path(args.dest_dir).joinpath(args.prefix_dir).joinpath("bin").joinpath("ectool"))
            )

        install_configs(str(pathlib.Path(args.dest_dir).joinpath(args.sysconf_dir).joinpath("fw-fanctrl")))
        install_services(
            str(pathlib.Path(args.dest_dir).joinpath(args.prefix_dir).joinpath("lib").joinpath("systemd")),
            args.executable_path,
            args.sysconf_dir,
            args.no_battery_sensors,
        )

        if not args.no_post_install:
            start_services()

    print("Success!")


if __name__ == "__main__":
    main()
