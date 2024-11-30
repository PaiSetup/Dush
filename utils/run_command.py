import subprocess
import shlex
import os
from utils.os_function import is_windows
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

    def __exit__(self, *args):
        os.environ = self._saved_env
        

def run_command(raw_command, *, shell=False, stdin=subprocess.PIPE, return_stdout=False, print_stdout=True, ignore_error=False, env={}, paths=[], generate_bat=False, timeout_seconds=None):
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

    with EnvSaver():
        # Set new env variables
        for key, value in env.items():
            os.environ[key] = str(value)

        # Prepend new paths to current PATH value
        if paths:
            new_paths = os.pathsep.join((str(x) for x in paths))
            current_path = os.environ.get("PATH", default="")
            if current_path:
                os.environ["PATH"] = new_paths + os.pathsep + current_path
            else:
                os.environ["PATH"] = new_paths

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

def open_url(url):
    if is_windows():
        os.startfile(url)
    else:
        run_command(f"xdg-open {url}")
