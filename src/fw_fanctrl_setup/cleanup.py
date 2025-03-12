import pathlib
import shutil
import sys

from fw_fanctrl import SOCKETS_FOLDER_PATH


def delete_file(
    dest_path: str,
):
    print(f"  > Deleting `{dest_path}` ...")
    try:
        pathlib.Path(dest_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"X > Failed to delete `{dest_path}`! Reason: `{e}`. Continuing.", file=sys.stderr)


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


def cleanup():
    print("Cleaning up files...")
    try:
        delete_folder(SOCKETS_FOLDER_PATH)
    except Exception as e:
        raise RuntimeError("Failed to clean up files") from e
