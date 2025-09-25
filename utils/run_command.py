import subprocess
import shlex
import os
from utils.os_function import is_windows, windows_only
from utils.paths import RaiiChdir
from contextlib import ExitStack
import platform
import contextlib
import datetime
import io
import sys


class Command:
    def __init__(self, command, process):
        self.command = command
        self.process = process
        self.execution_time = None
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


def print_run_command(raw_command, cwd):
    if cwd is None:
        cwd = os.getcwd()
    else:
        cwd = Path(cwd).absolute()
    print(f"Running command: {raw_command} (in directory {cwd})")


def run_command(
    raw_command,
    *,
    shell=False,
    stdin=Stdin.empty(),
    stdout=Stdout.print_to_console(),
    stderr=Stdout.print_to_console(),
    ignore_error=False,
    cwd=None,
    env={},
    paths=[],
    ld_library_paths=[],
    generate_bat=False,
    timeout_seconds=None,
):
    # Debug options
    if generate_bat:
        generate_bat_script(raw_command, cwd, paths, env)
    if framework.framework.get_framework_args().verbose:
        print_run_command(raw_command, cwd)

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
        if stdout_data is not None and (stdout.should_return or result.return_value != 0):
            result.stdout = stdout_data.decode("utf-8")
        if stderr_data is not None and (stderr.should_return or result.return_value != 0):
            result.stderr = stderr_data.decode("utf-8")

    # Raise exception on error
    if result.return_value != 0 and not ignore_error:
        raise CommandError(result)

    # Return the command object
    return result


class RedirectStdStreams:
    def __init__(self, new_fd, is_stdout):
        if is_stdout:
            self.stdout_target = new_fd
            self.stderr_target = None
        else:
            self.stdout_target = None
            self.stderr_target = new_fd
        self.saved_fds = {}

    def __enter__(self):
        self.saved_fds[1] = os.dup(1)  # save stdout fd
        self.saved_fds[2] = os.dup(2)  # save stderr fd

        if self.stdout_target:
            os.dup2(self.stdout_target.fileno(), 1)  # replace stdout
            sys.stdout = os.fdopen(os.dup(1), 'w', buffering=1)  # update Python's sys.stdout

        if self.stderr_target:
            os.dup2(self.stderr_target.fileno(), 2)  # replace stderr
            sys.stderr = os.fdopen(os.dup(2), 'w', buffering=1)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # restore stdout
        os.dup2(self.saved_fds[1], 1)
        os.close(self.saved_fds[1])
        sys.stdout = os.fdopen(os.dup(1), 'w', buffering=1)

        # restore stderr
        os.dup2(self.saved_fds[2], 2)
        os.close(self.saved_fds[2])
        sys.stderr = os.fdopen(os.dup(2), 'w', buffering=1)

def run_function(
    function,
    args=(),
    kwargs={},
    stdout=Stdout.print_to_console(),
    stderr=Stdout.print_to_console(),
    ignore_error=False,
):
    with ExitStack() as context:
        # Handle stdout/stderr redirection
        def redirect_output(popen_arg, is_stdout=True):
            # TODO is redirect_func needed when we have RedirectStdStreams?
            redirect_func = contextlib.redirect_stdout if is_stdout else contextlib.redirect_stderr

            match popen_arg:
                case None:
                    # Generated by print_to_console(). Do not override anything.
                    return None
                case subprocess.DEVNULL:
                    # Discard output
                    context.enter_context(redirect_func(None))
                    context.enter_context(RedirectStdStreams(None, is_stdout=is_stdout))
                    return None
                case subprocess.PIPE:
                    # Generated by return_back(). Capture output into a string buffer.
                    buffer = io.StringIO()
                    context.enter_context(redirect_func(buffer))
                    context.enter_context(RedirectStdStreams(buffer, is_stdout=is_stdout))
                    return buffer
                case _:
                    # Generated by print_to_file(). Popen arg is a file descriptor. Redirect output to the descriptor.
                    context.enter_context(redirect_func(popen_arg))
                    context.enter_context(RedirectStdStreams(popen_arg, is_stdout=is_stdout))
                    return None
        stdout_buffer = redirect_output(stdout.popen_arg, is_stdout=True)
        stderr_buffer = redirect_output(stderr.popen_arg, is_stdout=False)

        # Prepare command object
        result = Command(function.__name__, None)

        # Run the function and assign result
        begin_timestamp = datetime.datetime.now().replace(microsecond=0)
        try:
            function(*args, **kwargs)
            result.return_value = 0
        except:
            result.return_value = 1
        result.execution_time = datetime.datetime.now().replace(microsecond=0) - begin_timestamp

        # Assign outputs
        if stdout_buffer and (stdout.should_return or result.return_value != 0):
            result.stdout = stdout_buffer.getvalue()
        if stderr_buffer and (stderr.should_return or result.return_value != 0):
            result.stderr = stderr_buffer.getvalue()

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
