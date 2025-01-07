import sys

from src.CommandParser import CommandParser
from src.FanController import FanController
from src.hardwareController.EctoolHardwareController import EctoolHardwareController
from src.socketController.UnixSocketController import UnixSocketController


def main():
    args = CommandParser().parseArgs()

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
        )
        fan.run(debug=not args.silent)
    else:
        try:
            commandResult = socketController.sendViaClientSocket(" ".join(sys.argv[1:]))
            if commandResult:
                print(commandResult)
        except Exception as e:
            print(f"[Error] > An error occurred: {e}", file=sys.stderr)
            exit(1)


if __name__ == "__main__":
    main()
