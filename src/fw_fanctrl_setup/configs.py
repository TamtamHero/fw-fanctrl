import os
import pathlib
import shutil
import sys

from fw_fanctrl_setup import MAIN_INTERNAL_RESOURCES_PATH


def copy_configuration_file(configuration_file_path: str, dest_path: str, overwrite: bool = False):
    print(
        f"  > Copying `{configuration_file_path}` to `{dest_path}` {'' if overwrite else 'if it does not exists '}..."
    )
    try:
        os.makedirs(pathlib.Path(dest_path).parent, exist_ok=True)
        if not overwrite and os.path.isfile(dest_path):
            return
        shutil.copy(configuration_file_path, dest_path)
    except Exception as e:
        raise RuntimeError(f"Failed to copy `{configuration_file_path}` to `{dest_path}`") from e


def install_configs(configuration_directory_path: str):
    print("Installing configuration files")
    try:
        config_path = MAIN_INTERNAL_RESOURCES_PATH.joinpath("config.json")
        config_schema_path = MAIN_INTERNAL_RESOURCES_PATH.joinpath("config.schema.json")

        copy_configuration_file(
            config_path, str(pathlib.Path(configuration_directory_path).joinpath("config.json")), overwrite=False
        )
        copy_configuration_file(
            config_schema_path,
            str(pathlib.Path(configuration_directory_path).joinpath("config.schema.json")),
            overwrite=True,
        )
    except Exception as e:
        raise RuntimeError("Failed to install configuration files") from e


def delete_folder(
    dest_path: str,
):
    print(f"  > Deleting `{dest_path}` ...")
    try:
        shutil.rmtree(pathlib.Path(dest_path))
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"X > Failed to delete `{dest_path}`! Reason: `{e}`. Continuing.", file=sys.stderr)


def uninstall_configs(configuration_directory_path: str):
    print("Uninstalling configuration files")
    try:
        delete_folder(configuration_directory_path)
    except Exception as e:
        print(
            f"Failed to uninstall configuration files!{os.linesep}Reason: `{e}`.{os.linesep}Continuing.",
            file=sys.stderr,
        )
