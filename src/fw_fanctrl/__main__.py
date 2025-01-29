import sys

from fw_fanctrl.CommandParser import CommandParser
from fw_fanctrl.FanController import FanController
from fw_fanctrl.dto.command_result.CommandResult import CommandResult
from fw_fanctrl.enum.CommandStatus import CommandStatus
from fw_fanctrl.enum.OutputFormat import OutputFormat
from fw_fanctrl.hardwareController.EctoolHardwareController import EctoolHardwareController
from fw_fanctrl.socketController.UnixSocketController import UnixSocketController


def main():
    try:
        args = CommandParser().parseArgs()
    except Exception as e:
        _cre = CommandResult(CommandStatus.ERROR, str(e))
        print(_cre.toOutputFormat(OutputFormat.NATURAL), file=sys.stderr)
        exit(1)

    socketController = UnixSocketController()
    if args.socket_controller == "unix":
        socketController = UnixSocketController()

    if args.command == "run":
        hardwareController = EctoolHardwareController(noBatterySensorMode=args.no_battery_sensors)
        if args.hardware_controller == "ectool":
            hardwareController = EctoolHardwareController(noBatterySensorMode=args.no_battery_sensors)

        fan = FanController(
            hardwareController=hardwareController,
            socketController=socketController,
            configPath=args.config,
            strategyName=args.strategy,
            outputFormat=getattr(args, "output_format", None),
        )
        fan.run(debug=not args.silent)
    else:
        try:
            commandResult = socketController.sendViaClientSocket(" ".join(sys.argv[1:]))
            if commandResult:
                print(commandResult)
        except Exception as e:
            if str(e).startswith("[Error] >"):
                print(str(e), file=sys.stderr)
            else:
                _cre = CommandResult(CommandStatus.ERROR, str(e))
                print(_cre.toOutputFormat(getattr(args, "output_format", None)), file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    main()
