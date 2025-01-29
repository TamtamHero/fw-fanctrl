import argparse
import os
import sys
import textwrap

from fw_fanctrl import DEFAULT_CONFIGURATION_FILE_PATH
from fw_fanctrl.exception.UnknownCommandException import UnknownCommandException


class CommandParser:
    isRemote = True

    legacyParser = None
    parser = None

    def __init__(self, isRemote=False):
        self.isRemote = isRemote
        self.initParser()
        self.initLegacyParser()

    def initParser(self):
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

        commandsSubParser = self.parser.add_subparsers(dest="command")
        commandsSubParser.required = True

        if not self.isRemote:
            runCommand = commandsSubParser.add_parser(
                "run",
                description="run the service",
                formatter_class=argparse.RawTextHelpFormatter,
            )
            runCommand.add_argument(
                "strategy",
                help='name of the strategy to use e.g: "lazy" (use `print strategies` to list available strategies)',
                nargs=argparse.OPTIONAL,
            )
            runCommand.add_argument(
                "--config",
                "-c",
                help=f"the configuration file path (default: {DEFAULT_CONFIGURATION_FILE_PATH})",
                type=str,
                default=DEFAULT_CONFIGURATION_FILE_PATH,
            )
            runCommand.add_argument(
                "--silent",
                "-s",
                help="disable printing speed/temp status to stdout",
                action="store_true",
            )
            runCommand.add_argument(
                "--hardware-controller",
                "--hc",
                help="the hardware controller to use for fetching and setting the temp and fan(s) speed",
                type=str,
                choices=["ectool"],
                default="ectool",
            )
            runCommand.add_argument(
                "--no-battery-sensors",
                help="disable checking battery temperature sensors",
                action="store_true",
            )

        useCommand = commandsSubParser.add_parser("use", description="change the current strategy")
        useCommand.add_argument(
            "strategy",
            help='name of the strategy to use e.g: "lazy". (use `print strategies` to list available strategies)',
        )

        commandsSubParser.add_parser("reset", description="reset to the default strategy")
        commandsSubParser.add_parser("reload", description="reload the configuration file")
        commandsSubParser.add_parser("pause", description="pause the service")
        commandsSubParser.add_parser("resume", description="resume the service")

        printCommand = commandsSubParser.add_parser(
            "print",
            description="print the selected information",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        printCommand.add_argument(
            "print_selection",
            help=f"all - All details{os.linesep}current - The current strategy{os.linesep}list - List available strategies{os.linesep}speed - The current fan speed percentage{os.linesep}active - The service activity status",
            nargs="?",
            type=str,
            choices=["all", "active", "current", "list", "speed"],
            default="all",
        )

    def initLegacyParser(self):
        self.legacyParser = argparse.ArgumentParser(add_help=False)

        # avoid collision with the new parser commands
        def excludedPositionalArguments(value):
            if value in [
                "run",
                "use",
                "reload",
                "reset",
                "pause",
                "resume",
                "print",
            ]:
                raise argparse.ArgumentTypeError("%s is an excluded value" % value)
            return value

        bothGroup = self.legacyParser.add_argument_group("both")
        bothGroup.add_argument("_strategy", nargs="?", type=excludedPositionalArguments)
        bothGroup.add_argument("--strategy", nargs="?")

        runGroup = self.legacyParser.add_argument_group("run")
        runGroup.add_argument("--run", action="store_true")
        runGroup.add_argument("--config", type=str, default=DEFAULT_CONFIGURATION_FILE_PATH)
        runGroup.add_argument("--no-log", action="store_true")
        commandGroup = self.legacyParser.add_argument_group("configure")
        commandGroup.add_argument("--query", "-q", action="store_true")
        commandGroup.add_argument("--list-strategies", action="store_true")
        commandGroup.add_argument("--reload", "-r", action="store_true")
        commandGroup.add_argument("--pause", action="store_true")
        commandGroup.add_argument("--resume", action="store_true")
        commandGroup.add_argument(
            "--hardware-controller",
            "--hc",
            type=str,
            choices=["ectool"],
            default="ectool",
        )
        commandGroup.add_argument(
            "--socket-controller",
            "--sc",
            type=str,
            choices=["unix"],
            default="unix",
        )

    def parseArgs(self, args=None):
        values = None
        original_stderr = sys.stderr
        # silencing legacy parser output
        sys.stderr = open(os.devnull, "w")
        try:
            legacy_values = self.legacyParser.parse_args(args)
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
            if self.isRemote or values.command == "run":
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
