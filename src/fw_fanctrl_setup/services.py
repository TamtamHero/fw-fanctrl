import os
import pathlib
import subprocess
import sys

from fw_fanctrl_setup import SETUP_INTERNAL_RESOURCES_PATH


def copy_service_file(
    service_file_path: str,
    dest_path: str,
    python_path: str,
    python_script_installation_path: str,
    sysconf_dir: str,
    no_battery_sensor: bool,
    pipx: bool,
):
    print(f"  > Copying `{service_file_path}` to `{dest_path}` ...")
    try:
        os.makedirs(pathlib.Path(dest_path).parent, exist_ok=True)
        with open(dest_path, "w") as fp:
            service_content = pathlib.Path(service_file_path).read_text()
            service_content = service_content.replace(
                "%PYTHON_SCRIPT_INSTALLATION_PATH%", python_script_installation_path
            )
            service_content = service_content.replace("%SYSCONF_DIRECTORY%", sysconf_dir)
            service_content = service_content.replace(
                "%NO_BATTERY_SENSOR_OPTION%", "--no-battery-sensors" if no_battery_sensor else ""
            )
            service_content = service_content.replace("%PYTHON_PATH%", python_path if not pipx else "")
            fp.write(service_content)
        os.chmod(dest_path, os.stat(dest_path).st_mode | 0o111)
    except Exception as e:
        raise RuntimeError(f"Failed to copy `{service_file_path}` to `{dest_path}`") from e


def install_services(
    services_directory_path: str,
    python_path: str,
    python_script_installation_path: str,
    sysconf_dir: str,
    no_battery_sensor: bool,
    pipx: bool,
):
    print("Installing systemd services...")
    try:
        services_path = SETUP_INTERNAL_RESOURCES_PATH.joinpath("services")

        for service in services_path.iterdir():
            if not service.is_file():
                continue
            copy_service_file(
                service,
                str(pathlib.Path(services_directory_path).joinpath("system").joinpath(service.name)),
                python_path,
                python_script_installation_path,
                sysconf_dir,
                no_battery_sensor,
                pipx,
            )

        for subservice in services_path.rglob("*"):
            if not subservice.is_file() or subservice.parent == services_path:
                continue
            copy_service_file(
                subservice,
                str(
                    pathlib.Path(services_directory_path).joinpath(pathlib.Path(subservice.relative_to(services_path)))
                ),
                python_path,
                python_script_installation_path,
                sysconf_dir,
                no_battery_sensor,
                pipx,
            )
    except Exception as e:
        raise RuntimeError("Failed to install systemd services") from e


def systemctl_reload():
    subprocess.run(
        "systemctl daemon-reload",
        shell=True,
        text=True,
    ).check_returncode()


def start_services():
    print("Starting systemd services...")
    try:
        systemctl_reload()
        services_path = SETUP_INTERNAL_RESOURCES_PATH.joinpath("services")

        for service in services_path.iterdir():
            if not service.is_file():
                continue
            subprocess.run(
                f"systemctl enable --now '{pathlib.Path(service).name}'",
                shell=True,
                text=True,
            ).check_returncode()

        systemctl_reload()
    except Exception as e:
        raise RuntimeError("Failed to start systemd services") from e


def stop_services():
    print("Stopping systemd services...")
    try:
        systemctl_reload()
        services_path = SETUP_INTERNAL_RESOURCES_PATH.joinpath("services")

        for service in services_path.iterdir():
            if not service.is_file():
                continue
            try:
                subprocess.run(
                    f"systemctl disable --now '{pathlib.Path(service).name}'",
                    shell=True,
                    text=True,
                ).check_returncode()
            except Exception as e:
                print(
                    f"X > Failed to stop systemd service `{pathlib.Path(service).name}`!{os.linesep}Reason: `{e}`.{os.linesep}Continuing.",
                    file=sys.stderr,
                )

        systemctl_reload()
    except Exception as e:
        print(f"Failed to stop systemd services!{os.linesep}Reason: `{e}`.{os.linesep}Continuing.", file=sys.stderr)


def delete_service_file(
    dest_path: str,
):
    print(f"  > Deleting `{dest_path}` ...")
    try:
        pathlib.Path(dest_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"X > Failed to delete `{dest_path}`! Reason: `{e}`. Continuing.", file=sys.stderr)


def uninstall_services(
    services_directory_path: str,
):
    print("Uninstalling systemd services...")
    try:
        services_path = SETUP_INTERNAL_RESOURCES_PATH.joinpath("services")

        for service in services_path.iterdir():
            if not service.is_file():
                continue
            delete_service_file(
                str(pathlib.Path(services_directory_path).joinpath("system").joinpath(service.name)),
            )

        for subservice in services_path.rglob("*"):
            if not subservice.is_file() or subservice.parent == services_path:
                continue
            delete_service_file(
                str(
                    pathlib.Path(services_directory_path).joinpath(pathlib.Path(subservice.relative_to(services_path)))
                ),
            )
    except Exception as e:
        print(
            f"Failed to uninstall systemd services!{os.linesep}Reason: `{e}`.{os.linesep}Continuing.", file=sys.stderr
        )
