import subprocess
import shlex
import os
from utils.os_function import is_windows, windows_only
from utils.paths import RaiiChdir
from contextlib import ExitStack
import platform


class Command:
    def __init__(self, command, process):
        self.command = command
        self.process = process
        self.return_value = None
        self.stdout = None
        self.stderr = None

    def wait(self):
        if self._return_value is None:
            self._return_value = self._process.wait()
        return self._return_value



class CommandErrorBase(Exception):
    def __init__(self, command):
        self._command = command

    def __str__(self):
        result = f"command: {self._command.command}"
        if self._command.stdout:
            result += f"\n\nstdout: {self._command.stdout}"
        if self._command.stderr:
            result += f"\n\nstderr: {self._command.stderr}"
        return result


class CommandTimeout(CommandErrorBase):
    pass


class CommandError(CommandErrorBase):
    pass


class Stdin:
    def __init__(self, popen_arg, communicate_arg):
        self.popen_arg = popen_arg
        self.communicate_arg = communicate_arg

    @staticmethod
    def empty():
        return Stdin(None, None)

    @staticmethod
    def file(file_handle):
        return Stdin(file_handle, None)

    @staticmethod
    def string(content):
        return Stdin(subprocess.PIPE, bytes(content, "utf-8"))


class Stdout:
    def __init__(self, popen_arg, should_return):
        self.popen_arg = popen_arg
        self.should_return = should_return

    @staticmethod
    def ignore():
        return Stdout(subprocess.PIPE, False)  # We could use DEVNULL, but we need the outputs to throw errors

    @staticmethod
    def return_back():
        return Stdout(subprocess.PIPE, True)

    @staticmethod
    def print_to_console():
        return Stdout(None, False)

    @staticmethod
    def print_to_file(file_handle):
        return Stdout(file_handle, False)


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


def generate_bat_script(raw_command, cwd, paths, env):
    separator = "------------------------------"
    lines = [
        separator,
        "@echo off",
        "",
    ]

    if cwd:
        lines.append("REM set directory")
        lines.append(f'cd "{cwd}"')

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

def run_command(
    raw_command,
    *,
    shell=False,
    stdin=Stdin.empty(),
    stdout=Stdout.print_to_console(),
    stderr=Stdout.print_to_console(),
    ignore_error=False,
    cwd = None,
    env={},
    paths=[],
    ld_library_paths=[],
    generate_bat=False,
    timeout_seconds=None
):
    # Debug options
    if generate_bat:
        generate_bat_script(raw_command, cwd, paths, env)

    # Prepare command to execute
    if not shell and platform.system() != "Windows":
        command = shlex.split(raw_command)
    else:
        command = raw_command

    # Create ExitStack for conditional context managers
    with ExitStack() as context:
        # Set cwd
        if cwd:
            context.enter_context(RaiiChdir(cwd))

        # Set environment
        if env or paths or ld_library_paths:
            env_state = context.enter_context(EnvSaver())

            # Set key/value environment variables
            for key, value in env.items():
                env_state.set(key, value)

            # Prepend new paths to current PATH and LD_LIBRARY_PATH values
            env_state.prepend_paths("PATH", os.pathsep, paths)
            env_state.prepend_paths("LD_LIBRARY_PATH", ':', ld_library_paths)

        # Execute the command and wait for it to return
        process = subprocess.Popen(command, shell=shell, stdin=stdin.popen_arg, stdout=stdout.popen_arg, stderr=stderr.popen_arg)
        result = Command(raw_command, process)
        try:
            (stdout_data, stderr_data) = process.communicate(input=stdin.communicate_arg, timeout=timeout_seconds)
            result.return_value = process.wait()
        except subprocess.TimeoutExpired:
            process.kill()
            raise CommandTimeout(result)

        # Process output
        if stdout_data is not None:
            stdout_data = stdout_data.decode("utf-8")
        if stderr_data is not None:
            stderr_data = stderr_data.decode("utf-8")
        if stdout.should_return:
            result.stdout = stdout_data
        if stderr.should_return:
            result.stderr = stderr_data

    # Raise exception on error
    if result.return_value != 0 and not ignore_error:
        raise CommandError(result)

    # Return the command object
    return result


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
