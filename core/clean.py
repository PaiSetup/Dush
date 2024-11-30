import shutil

class IncorrectDirectoryError(Exception):
    pass

class CleanupPermissionError(Exception):
    def __init__(self, file):
        self.file = file

    def __str__(self):
        return f'cannot remove {self.file}'

def clean(build_dir):
    if not build_dir.exists():
        return
    if not build_dir.is_dir():
        raise IncorrectDirectoryError(f"{build_dir} is not a directory")

    print(f"Cleaning {build_dir}")
    try:
        shutil.rmtree(build_dir)
    except PermissionError as e:
        raise CleanupPermissionError(e.filename)
