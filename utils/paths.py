import os
from pathlib import Path

class PredefinedPath:
    def __init__(self, required, is_directory, lazy_resolve):
        self._path = None
        self._required = required
        self._is_directory = is_directory

        if not lazy_resolve:
            self.get()

    def _resolve(self):
        raise NotImplementedError()

    def get(self):
        if self._path is None:
            self._path = self._resolve()

            if self._required:
                if self._path is None:
                    raise ValueError("Predefined path is missing.")
                if self._is_directory and not self._path.is_dir():
                    raise FileNotFoundError(f"Predefined file path is invalid. {self._path}")
                if not self._is_directory and not self._path.is_file():
                    raise FileNotFoundError(f"Predefined directory path is invalid. {self._path}")

        return self._path

    def __str__(self):
        return str(self.get())

    def __truediv__(self, subdir):
        return Path(str(self)) / subdir


class HardcodedPath(PredefinedPath):
    def __init__(self, path, required=True, is_directory=True, lazy_resolve=True):
        self._hardcoded_path = path
        super().__init__(required, is_directory, lazy_resolve)

    def _resolve(self):
        return Path(self._hardcoded_path)

class EnvPath(PredefinedPath):
    def __init__(self, env_name, required=True, is_directory=True, lazy_resolve=True):
        self._env_name = env_name
        super().__init__(required, is_directory, lazy_resolve)

    def _resolve(self):
        try:
            return Path(os.environ[self._env_name])
        except KeyError:
            if self._required:
                raise KeyError(f'Cannot find path. Please define it in {self._env_name} environment variable.')
            else:
                return None

class RaiiChdir:
    def __init__(self, new_cwd):
        self._new_cwd = new_cwd

    def __enter__(self):
        self._saved_cwd = os.getcwd()
        try:
            os.chdir(self._new_cwd)
            self.success = True
        except:
            self.success = False
        self.cwd = os.getcwd()
        return self

    def __exit__(self, *args):
        os.chdir(self._saved_cwd)
