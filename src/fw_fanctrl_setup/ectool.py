import hashlib
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from urllib.request import urlopen

from fw_fanctrl_setup import SETUP_INTERNAL_RESOURCES_PATH


def download(save_dir: str, url: str, sha256_checksum: str):
    with urlopen(url) as response:
        with open(file=pathlib.Path(save_dir).joinpath("ectool_artifact.zip"), mode="w+b") as file:
            file.write(response.read())
            file.seek(0)
            sha256 = hashlib.sha256()
            while chunk := file.read():
                sha256.update(chunk)
            if sha256_checksum != sha256.hexdigest():
                raise RuntimeError(f"SHA256 checksum mismatch: '{sha256.hexdigest()}', expected '{sha256_checksum}'")
            return file.name


def extract(save_dir: str, zip_path: str, to_extract: str):
    with zipfile.ZipFile(zip_path) as zip_file:
        return zip_file.extract(to_extract, save_dir)


def download_ectool_artifact(save_dir: str, job_id: int, sha256_checksum: str):
    print("  > Downloading...")
    try:
        return download(
            save_dir,
            f"https://gitlab.howett.net/DHowett/ectool/-/jobs/{job_id}/artifacts/download?file_type=archive",
            sha256_checksum,
        )
    except Exception as e:
        raise RuntimeError("Failed to download `ectool`") from e


def extract_ectool_artifact(save_dir: str, artifact_zip_path: str):
    print("  > Extracting...")
    try:
        return extract(save_dir, artifact_zip_path, "_build/src/ectool")
    except Exception as e:
        raise RuntimeError("Failed to extract `ectool`") from e


def copy_ectool(ectool_path: str, dest_path: str):
    print(f"  > Copying `{ectool_path}` to `{dest_path}` ...")
    try:
        os.makedirs(pathlib.Path(dest_path).parent, exist_ok=True)
        shutil.copy(ectool_path, dest_path)
        os.chmod(dest_path, os.stat(dest_path).st_mode | 0o111)
    except Exception as e:
        raise RuntimeError(f"Failed to copy `{ectool_path}` to `{dest_path}`") from e


def install_ectool(ectool_installation_path: str):
    print("Installing `ectool`")
    try:
        ectool_job_id = int(
            SETUP_INTERNAL_RESOURCES_PATH.joinpath("fetch")
            .joinpath("ectool")
            .joinpath("linux")
            .joinpath("gitlab_job_id")
            .read_text()
        )

        ectool_sha256_sum = (
            SETUP_INTERNAL_RESOURCES_PATH.joinpath("fetch")
            .joinpath("ectool")
            .joinpath("linux")
            .joinpath("hash.sha256")
            .read_text()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_zip_path = download_ectool_artifact(temp_dir, ectool_job_id, ectool_sha256_sum)
            extracted_path = extract_ectool_artifact(temp_dir, artifact_zip_path)
            copy_ectool(extracted_path, ectool_installation_path)
    except Exception as e:
        raise RuntimeError("Failed to install `ectool`") from e


def ectool_auto_behaviour(ectool_installation_path: str, warning: bool):
    print("Resetting the fan control behaviour to `auto`")
    try:
        subprocess.run(
            f"{shlex.quote(ectool_installation_path)} autofanctrl",
            shell=True,
            text=True,
        ).check_returncode()
    except Exception as e:
        print(
            f"Failed to reset the fan control behaviour to `auto`.{os.linesep}Reason: `{e}`.{os.linesep}Continuing.",
            file=sys.stderr,
        )
        if not warning:
            print(
                f"===================================================================={os.linesep}"
                f"PLEASE RESTART YOUR COMPUTER TO BRING BACK THE DEFAULT FAN BEHAVIOUR{os.linesep}"
                f"FAILING TO DO SO MIGHT CAUSE OVERHEATING!{os.linesep}"
                "====================================================================",
                file=sys.stderr,
            )


def delete_file(
    dest_path: str,
):
    print(f"  > Deleting `{dest_path}` ...")
    try:
        pathlib.Path(dest_path).unlink(missing_ok=True)
    except Exception as e:
        print(f"X > Failed to delete `{dest_path}`! Reason: `{e}`. Continuing.", file=sys.stderr)


def uninstall_ectool(ectool_installation_path: str):
    print("Uninstalling `ectool`")
    try:
        delete_file(ectool_installation_path)
    except Exception as e:
        print(f"Failed to install `ectool`!{os.linesep}Reason: `{e}`.{os.linesep}Continuing.", file=sys.stderr)
