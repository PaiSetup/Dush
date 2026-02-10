import shutil
import tempfile
from pathlib import Path

from dush.utils import LocalOrRemotePath, run_command


class IncorrectFileError(Exception):
    pass


def install(src_dir: Path | LocalOrRemotePath, dst_dir: LocalOrRemotePath, filenames: list[str], tmp_dir: LocalOrRemotePath, *, follow_symlinks=True):
    if type(src_dir) is LocalOrRemotePath:
        if src_dir.is_mounted():
            src_dir = src_dir.get_mounted_full_path()
        else:
            raise IncorrectFileError("Ssh source directory is not supported")

    if dst_dir.is_ssh():
        files = [f"'{str(Path(src_dir) / f)}'" for f in filenames]
        files = " ".join(files)
        command = f"scp {files} {dst_dir.get_ssh_full_path()}"
        print(command)
        run_command(command)
    else:
        for filename_raw in filenames:
            filename = Path(filename_raw)
            src = src_dir / filename
            dst = dst_dir.get_mounted_full_path() / filename

            if not src.is_file():
                raise IncorrectFileError(f"File to install {src} does not exist.")
            if dst.is_dir():
                raise IncorrectFileError(f"Destination file {dst} is a directory.")

            try:
                print(f"Installing {src} -> {dst}")
                if not follow_symlinks:
                    dst.unlink(missing_ok=True)  # symlinks cannot be overwritten for some reason
                shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
            except PermissionError:
                if tmp_dir is None:
                    raise

                with tempfile.NamedTemporaryFile(
                    prefix=f"{filename.stem}_", suffix=filename.suffix, dir=tmp_dir.get_mounted_full_path(), delete=True
                ) as dst_tmp:
                    dst_tmp_path = Path(dst_tmp.name)
                dst_tmp_path.unlink(
                    missing_ok=True
                )  # This shouldn't be needed, because NamedTemporaryFile should've already removed the file, but it sometimes doesn't do it on remote drives

                print(f"  Permission error. Try to move destination file to a tmp file {dst_tmp_path}")
                dst.rename(dst_tmp_path)

                try:
                    print("  Retry installation")
                    shutil.copyfile(src, dst)
                except:
                    print("  Installation failed. Recovering dst file from tmp location")
                    dst_tmp_path.rename(dst)
                    raise IncorrectFileError("Could not install file even after moving destination file to a tmp file")
