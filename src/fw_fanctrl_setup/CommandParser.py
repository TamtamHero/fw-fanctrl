import argparse
import os
import pathlib
import textwrap


class CommandParser:
    parser = None

    def __init__(self):
        self.init_parser()

    def init_parser(self):
        self.parser = argparse.ArgumentParser(
            prog="fw-fanctrl-setup",
            description="install or remove fw-fanctrl required additional files on the system.",
            epilog=textwrap.dedent(
                "obtain more help about a command or subcommand using `fw-fanctrl-setup <command> [subcommand...] -h/--help`"
            ),
            formatter_class=argparse.RawTextHelpFormatter,
        )

        command_sub_parser = self.parser.add_subparsers(dest="command")

        run_command = command_sub_parser.add_parser(
            "run",
            description="run the installation/uninstallation command",
            formatter_class=argparse.RawTextHelpFormatter,
        )

        run_command.add_argument(
            "--remove", "-r", help="uninstall additional files from the system", action="store_true"
        )
        run_command.add_argument(
            "--prefix-dir", "-p", help="specify an installation prefix directory", type=str, default="/usr"
        )
        run_command.add_argument(
            "--dest-dir", "-d", help="specify an installation destination directory", type=str, default=""
        )
        run_command.add_argument(
            "--sysconf-dir", "-s", help="specify a default configuration directory", type=str, default="/etc"
        )
        run_command.add_argument("--no-sudo", help="disable root privilege requirement", action="store_true")
        run_command.add_argument("--no-ectool", help="disable ectool installation", action="store_true")
        run_command.add_argument("--no-pre-uninstall", help="disable pre-uninstall process", action="store_true")
        run_command.add_argument("--no-post-install", help="disable post-install process", action="store_true")
        run_command.add_argument(
            "--no-battery-sensors", help="disable checking battery temperature sensors", action="store_true"
        )
        run_command.add_argument("--python-path", help="python executable path", type=str, default="/usr/bin/python3")
        run_command.add_argument("--executable-path", help="`fw-fanctrl` executable path", type=str)
        run_command.add_argument(
            "--keep-config", help="do not delete the existing configuration during uninstallation", action="store_true"
        )
        run_command.add_argument("--pipx", help="specify the use of pipx", action="store_true")

    def parse_args(self, args=None):
        parsed_args = self.parser.parse_args(args)
        if parsed_args.command is None:
            self.parser.error(
                f"Error: Missing 'run' subcommand.{os.linesep}"
                f"ONLY USE THIS COMMAND IF 'fw-fanctrl' WAS INSTALLED MANUALLY!{os.linesep}"
                "OTHERWISE USE YOUR PACKAGE MANAGER TO MANAGE/REMOVE IT!"
            )
        if parsed_args.executable_path is None:
            parsed_args.executable_path = str(
                pathlib.Path(parsed_args.dest_dir)
                .joinpath(parsed_args.prefix_dir)
                .joinpath("bin")
                .joinpath("fw-fanctrl")
            )
        if not parsed_args.remove:
            parsed_args.keep_config = True
        return parsed_args
