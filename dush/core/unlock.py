import shutil
import tempfile
from pathlib import Path

from dush.utils import LocalOrRemotePath


def unlock(file_path, tmp_dir, keep=True):
    if isinstance(file_path, LocalOrRemotePath):
        file_path = file_path.get_mounted_full_path()
    if isinstance(tmp_dir, LocalOrRemotePath):
        tmp_dir = tmp_dir.get_mounted_full_path()

    if not file_path.exists():
        return

    print(f"Unlocking {file_path}")

    # Generate a tmp file name
    file_path = Path(file_path)
    with tempfile.NamedTemporaryFile(prefix=f"{file_path.stem}_", suffix=file_path.suffix, dir=tmp_dir, delete=False) as tmp:
        tmp_path = Path(tmp.name)

    # Move our locked file to the tmp path
    file_path.replace(tmp_path)

    # Copy it back. The file will be the same, but the locked file is left in tmp.
    if keep:
        shutil.copyfile(tmp_path, file_path)
