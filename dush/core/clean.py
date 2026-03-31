import shutil
import os
import stat


class IncorrectDirectoryError(Exception):
    pass


class CleanupPermissionError(Exception):
    def __init__(self, file):
        self.file = file

    def __str__(self):
        return f"cannot remove {self.file}"


def clean(build_dir, ignore_errors=False):
    if not build_dir.exists():
        return
    if not build_dir.is_dir():
        raise IncorrectDirectoryError(f"{build_dir} is not a directory")

    def force_remove_readonly(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    ignore_errors_str = " (ignoring errors)" if ignore_errors else ""
    print(f"Cleaning {build_dir}{ignore_errors_str}")
    try:
        shutil.rmtree(build_dir, ignore_errors=ignore_errors, onexc=force_remove_readonly)
    except PermissionError as e:
        raise CleanupPermissionError(e.filename)
