import shlex
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
        args = CommandParser().parse_args(shlex.split(shlex.join(sys.argv[1:])))
    except Exception as e:
        _cre = CommandResult(CommandStatus.ERROR, str(e))
        print(_cre.to_output_format(OutputFormat.NATURAL), file=sys.stderr)
        exit(1)

    socket_controller = UnixSocketController()
    if args.socket_controller == "unix":
        socket_controller = UnixSocketController()

    if args.command == "run":
        hardware_controller = EctoolHardwareController(no_battery_sensor_mode=args.no_battery_sensors)
        if args.hardware_controller == "ectool":
            hardware_controller = EctoolHardwareController(no_battery_sensor_mode=args.no_battery_sensors)

        fan = FanController(
            hardware_controller=hardware_controller,
            socket_controller=socket_controller,
            config_path=args.config,
            strategy_name=args.strategy,
            output_format=getattr(args, "output_format", None),
        )
        fan.run(debug=not args.silent)
    else:
        try:
            command_result = socket_controller.send_via_client_socket(shlex.join(sys.argv[1:]))
            if command_result:
                print(command_result)
        except Exception as e:
            if str(e).startswith("[Error] >"):
                print(str(e), file=sys.stderr)
            else:
                _cre = CommandResult(CommandStatus.ERROR, str(e))
                print(_cre.to_output_format(getattr(args, "output_format", None)), file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    main()
