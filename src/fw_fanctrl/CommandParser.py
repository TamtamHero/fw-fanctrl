import argparse
import os
import sys
import textwrap

from fw_fanctrl import DEFAULT_CONFIGURATION_FILE_PATH
from fw_fanctrl.enum.OutputFormat import OutputFormat
from fw_fanctrl.exception.UnknownCommandException import UnknownCommandException


class CommandParser:
    is_remote = True

    legacy_parser = None
    parser = None

    def __init__(self, is_remote=False):
        self.is_remote = is_remote
        self.init_parser()
        self.init_legacy_parser()

    def init_parser(self):
        self.parser = argparse.ArgumentParser(
            prog="fw-fanctrl",
            description="control Framework's laptop fan(s) with a speed curve",
            epilog=textwrap.dedent(
                "obtain more help about a command or subcommand using `fw-fanctrl <command> [subcommand...] -h/--help`"
            ),
            formatter_class=argparse.RawTextHelpFormatter,
        )
        self.parser.add_argument(
            "--socket-controller",
            "--sc",
            help="the socket controller to use for communication between the cli and the service",
            type=str,
            choices=["unix"],
            default="unix",
        )
        self.parser.add_argument(
            "--output-format",
            help="the output format to use for the command result",
            type=lambda s: (lambda: OutputFormat[s])() if hasattr(OutputFormat, s) else s,
            choices=list(OutputFormat._member_names_),
            default=OutputFormat.NATURAL,
        )

        commands_sub_parser = self.parser.add_subparsers(dest="command")
        commands_sub_parser.required = True

        if not self.is_remote:
            run_command = commands_sub_parser.add_parser(
                "run",
                description="run the service",
                formatter_class=argparse.RawTextHelpFormatter,
            )
            run_command.add_argument(
                "strategy",
                help='name of the strategy to use e.g: "lazy" (use `print strategies` to list available strategies)',
                nargs=argparse.OPTIONAL,
            )
            run_command.add_argument(
                "--config",
                "-c",
                help=f"the configuration file path (default: {DEFAULT_CONFIGURATION_FILE_PATH})",
                type=str,
                default=DEFAULT_CONFIGURATION_FILE_PATH,
            )
            run_command.add_argument(
                "--silent",
                "-s",
                help="disable printing speed/temp status to stdout",
                action="store_true",
            )
            run_command.add_argument(
                "--hardware-controller",
                "--hc",
                help="the hardware controller to use for fetching and setting the temp and fan(s) speed",
                type=str,
                choices=["ectool"],
                default="ectool",
            )
            run_command.add_argument(
                "--no-battery-sensors",
                help="disable checking battery temperature sensors",
                action="store_true",
            )

        use_command = commands_sub_parser.add_parser("use", description="change the current strategy")
        use_command.add_argument(
            "strategy",
            help='name of the strategy to use e.g: "lazy". (use `print list` to list available strategies)',
        )

        commands_sub_parser.add_parser("reset", description="reset to the default strategy")
        commands_sub_parser.add_parser("reload", description="reload the configuration file")
        commands_sub_parser.add_parser("pause", description="pause the service")
        commands_sub_parser.add_parser("resume", description="resume the service")

        print_command = commands_sub_parser.add_parser(
            "print",
            description="print the selected information",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        print_command.add_argument(
            "print_selection",
            help=f"all - All details{os.linesep}current - The current strategy{os.linesep}list - List available strategies{os.linesep}speed - The current fan speed percentage{os.linesep}active - The service activity status",
            nargs="?",
            type=str,
            choices=["all", "active", "current", "list", "speed"],
            default="all",
        )

        set_config_command = commands_sub_parser.add_parser(
            "set_config", description="replace the service configuration with the provided one"
        )
        set_config_command.add_argument(
            "provided_config",
            help="must be a valid JSON configuration",
            type=str,
        )

    def init_legacy_parser(self):
        self.legacy_parser = argparse.ArgumentParser(add_help=False)

        # avoid collision with the new parser commands
        def excluded_positional_arguments(value):
            if value in [
                "run",
                "use",
                "reload",
                "reset",
                "pause",
                "resume",
                "print",
                "set_config",
            ]:
                raise argparse.ArgumentTypeError("%s is an excluded value" % value)
            return value

        both_group = self.legacy_parser.add_argument_group("both")
        both_group.add_argument("_strategy", nargs="?", type=excluded_positional_arguments)
        both_group.add_argument("--strategy", nargs="?")

        run_group = self.legacy_parser.add_argument_group("run")
        run_group.add_argument("--run", action="store_true")
        run_group.add_argument("--config", type=str, default=DEFAULT_CONFIGURATION_FILE_PATH)
        run_group.add_argument("--no-log", action="store_true")
        command_group = self.legacy_parser.add_argument_group("configure")
        command_group.add_argument("--query", "-q", action="store_true")
        command_group.add_argument("--list-strategies", action="store_true")
        command_group.add_argument("--reload", "-r", action="store_true")
        command_group.add_argument("--pause", action="store_true")
        command_group.add_argument("--resume", action="store_true")
        command_group.add_argument(
            "--hardware-controller",
            "--hc",
            type=str,
            choices=["ectool"],
            default="ectool",
        )
        command_group.add_argument(
            "--socket-controller",
            "--sc",
            type=str,
            choices=["unix"],
            default="unix",
        )

    def parse_args(self, args=None):
        original_stderr = sys.stderr
        # silencing legacy parser output
        sys.stderr = open(os.devnull, "w")
        try:
            legacy_values = self.legacy_parser.parse_args(args)
            if legacy_values.strategy is None:
                legacy_values.strategy = legacy_values._strategy
            # converting legacy values into new ones
            values = argparse.Namespace()
            values.socket_controller = legacy_values.socket_controller
            values.output_format = OutputFormat.NATURAL
            if legacy_values.query:
                values.command = "print"
                values.print_selection = "current"
            if legacy_values.list_strategies:
                values.command = "print"
                values.print_selection = "list"
            if legacy_values.resume:
                values.command = "resume"
            if legacy_values.pause:
                values.command = "pause"
            if legacy_values.reload:
                values.command = "reload"
            if legacy_values.run:
                values.command = "run"
                values.silent = legacy_values.no_log
                values.hardware_controller = legacy_values.hardware_controller
                values.config = legacy_values.config
                values.strategy = legacy_values.strategy
            if not hasattr(values, "command") and legacy_values.strategy is not None:
                values.command = "use"
                values.strategy = legacy_values.strategy
            if not hasattr(values, "command"):
                raise UnknownCommandException("not a valid legacy command")
            if self.is_remote or values.command == "run":
                # Legacy commands do not support other formats than NATURAL, so there is no need to use a CommandResult.
                print(
                    "[Warning] > this command is deprecated and will be removed soon, please use the new command format instead ('fw-fanctrl -h' for more details)."
                )
        except (SystemExit, Exception):
            sys.stderr = original_stderr
            values = self.parser.parse_args(args)
        finally:
            sys.stderr = original_stderr
        return values
