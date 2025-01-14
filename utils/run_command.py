import subprocess
import shlex
import os
from utils.os_function import is_windows, windows_only
import platform


class CommandError(Exception):
    def __init__(self, output=None, command=None):
        self.stdout = self.stderr = None
        if output is not None:
            if output[0] is not None:
                self.stdout = output[0].decode("utf-8")
            if output[1] is not None:
                self.stderr = output[1].decode("utf-8")
        if command is not None:
            self.command = command

    def __str__(self):
        lines = []
        if self.stdout:
            lines.append(f"stdout: {self.stdout}")
        if self.stderr:
            lines.append(f"stderr: {self.stderr}")
        if self.command:
            lines.append(f"command: {self.command}")
        return '\n'.join(lines)


class CommandTimeout(Exception):
    pass

class EnvSaver:
    def __enter__(self):
        self._saved_env = os.environ
        return self

    def prepend_paths(self, env_name, separator, paths):
        if not paths:
            return

        new_paths = separator.join((str(x) for x in paths))
        current_path = os.environ.get(env_name, default="")
        if current_path:
            os.environ[env_name] = new_paths + separator + current_path
        else:
            os.environ[env_name] = new_paths

    def set(self, env_name, value):
        os.environ[str(env_name)] = str(value)

    def __exit__(self, *args):
        os.environ = self._saved_env


def run_command(raw_command, *, shell=False, stdin=subprocess.PIPE, return_stdout=False, print_stdout=True, ignore_error=False, env={}, paths=[], ld_library_paths=[], generate_bat=False, timeout_seconds=None):
    if generate_bat:
        separator = "------------------------------"
        lines = [
            separator,
            "@echo off",
            "",
        ]

        if paths:
            lines.append("REM Setup paths")
            for p in reversed(paths):
                lines.append(f"set PATH={p};%PATH%")
            lines.append("")

        if env:
            lines.append("REM Setup environment variables")
            for key, value in env.items():
                lines.append(f"set {key}={value}")
            lines.append("")

        lines.append("@echo on")
        lines.append(f"call {raw_command}")
        lines.append(separator)

        for line in lines:
            print(line)

    if not shell and platform.system() != "Windows":
        command = shlex.split(raw_command)
    else:
        command = raw_command

    if return_stdout and print_stdout:
        raise ValueError("Returning and printing stdout at the same time is not supported")
    stdout = subprocess.PIPE
    if print_stdout:
        stdout = None

    with EnvSaver() as env_state:
        # Set new env variables
        for key, value in env.items():
            env_state.set(key, value)

        # Prepend new paths to current PATH value
        env_state.prepend_paths("PATH", os.pathsep, paths)
        env_state.prepend_paths("LD_LIBRARY_PATH", ':', ld_library_paths)

        # Execute the command and wait for it to return
        process = subprocess.Popen(command, shell=shell, stdin=stdin, stdout=stdout, stderr=stdout)
        try:
            output = process.communicate(timeout=timeout_seconds)
            return_value = process.wait()
        except subprocess.TimeoutExpired:
            process.kill()
            raise CommandTimeout()

    if return_value != 0 and not ignore_error:
        raise CommandError(output=output, command=raw_command)

    if return_stdout and output[0] != None:
        return output[0].decode("utf-8")

@windows_only
def wrap_command_with_vcvarsall(vc_varsall_path, command, verbose=False):
    vc_varsall_command = f'"{vc_varsall_path}" amd64'

    if verbose:
        wrapped_command = [
            vc_varsall_command,
            "echo",
            "echo Testing 'where cl'",
            "where cl",
            command,
        ]
    else:
        wrapped_command = [
            f"{vc_varsall_command} > nul 2>&1",
            command,
        ]
    wrapped_command = ' & '.join(wrapped_command)
    wrapped_command = f'cmd /C "{wrapped_command}"' # Should probably escape quotes...
    return wrapped_command

def open_url(url):
    if is_windows():
        os.startfile(url)
    else:
        run_command(f"xdg-open {url}")
