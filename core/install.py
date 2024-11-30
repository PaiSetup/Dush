from pathlib import Path
import shutil
import tempfile
from utils.run_command import run_command

class IncorrectFileError(Exception):
    pass

def _is_scp(dst_dir):
    colon_pos = str(dst_dir).find(":")
    if colon_pos == -1:
        return False

    # Before the colon there could be a host name as in "host:/home/johndoe" or a drive name
    # as in "C:\develop\linux". We make an assumption that host names are never one-letter.
    # TODO: create some structure for scp paths, so we don't have to have such heuristics.
    match colon_pos:
        case 0:
            raise ValueError("Directory cannot start with a colon")
        case 1:
            return False # One letter before colon, probably a drive name
        case _:
            return True # Multiple letter before colon, probably host name for scp

def install(src_dir, dst_dir, filenames, tmp_dir):
    if _is_scp(dst_dir):
        files = [ f"'{str(Path(src_dir) / f)}'" for f in filenames]
        files = ' '.join(files)
        command = f"scp {files} {dst_dir}"
        print(command)
        run_command(command)
    else:
        for filename_raw in filenames:
            filename = Path(filename_raw)
            src = src_dir / filename
            dst = dst_dir / filename

            if not src.is_file():
                raise IncorrectFileError(f"File to install {src} does not exist.")
            if dst.is_dir():
                raise IncorrectFileError(f"Destination file {dst} is a directory.")

            try:
                print(f"Installing {src} -> {dst}")
                shutil.copyfile(src, dst)
            except PermissionError:
                if tmp_dir is None:
                    raise

                with tempfile.NamedTemporaryFile(prefix=f"{filename.stem}_", suffix=filename.suffix, dir=tmp_dir, delete=True) as dst_tmp:
                    dst_tmp_path = Path(dst_tmp.name)
                dst_tmp_path.unlink(missing_ok=True) # This shouldn't be needed, because NamedTemporaryFile should've already removed the file, but it sometimes doesn't do it on remote drives

                print(f"  Permission error. Try to move destination file to a tmp file {dst_tmp_path}")
                dst.rename(dst_tmp_path)

                try:
                    print("  Retry installation")
                    shutil.copyfile(src, dst)
                except:
                    print("  Installation failed. Recovering dst file from tmp location")
                    dst_tmp_path.rename(dst)
                    raise IncorrectFileError("Could not install file even after moving destination file to a tmp file")
