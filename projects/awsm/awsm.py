import tempfile
from pathlib import Path

import core
from framework import *
from utils import *

# ----------------------------------------------------------- Helpers for commands
is_main = __name__ == "__main__"
project_repositories.load(Path(__file__).parent)

qt_path = EnvPath("QT_PATH", is_directory=True, required=False)
vc_varsall_path = EnvPath("VC_VARSALL_PATH", is_directory=False, required=False)


@linux_only
def get_build_dir(project_dir, config):
    return project_dir / f"build.{config.build_type}"


def get_install_dir(build_dir):
    return build_dir / "install"


# ----------------------------------------------------------- Commands
@command
def cmake(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    install_dir = get_install_dir(build_dir)

    cmake_options = [
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
    ]
    core.cmake(config, build_dir, project_dir, additional_cmake_options=cmake_options)


@command
def compile(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)

    core.compile_with_make("", build_dir)
    core.compile_with_make("install", build_dir)


@command
def test(config="", use_default_config=False):
    config = interpret_arg(config, BuildConfig, "config")
    use_default_config = interpret_arg(use_default_config, bool, "use_default_config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    install_dir = get_install_dir(build_dir)
    binary_path = install_dir / "bin/awesome"
    script_path = Path(__file__).parent / "run_in_xephyr.sh"

    display = None
    for display_idx in range(5, 16):
        lock_file = Path(f"/tmp/.X{display_idx}-lock")
        if not lock_file.exists():
            display = f":{display_idx}"
            break

    if display is None:
        raise ValueError("No X displays available")

    run_command(f"{script_path} {binary_path} {display} {int(use_default_config)}")


@command
def clear_test_xorg_locks():
    # This isn't very safe, but there's a low chance anything really useful runs on these displays
    # These lock files are often left behind by Xephyr.
    for display_idx in range(5, 16):
        lock_file = Path(f"/tmp/.X{display_idx}-lock")
        if lock_file.exists():
            print(f"Removing {lock_file}")
            run_command(f"sudo rm {lock_file}")


@command
def run_integration_tests(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)

    core.compile_with_make("", build_dir)

    env = {
        "CMAKE_BINARY_DIR": build_dir,
        "LUA": "lua",
    }

    run_command("tests/run.sh", cwd=project_dir, env=env)


# ----------------------------------------------------------- Main procedure
if is_main:
    BuildConfig.configure(
        [Compiler.Makefiles],
        [Bitness.x64],
        [BuildType.Debug, BuildType.Release],
        Compiler.Makefiles,
        Bitness.x64,
        BuildType.Debug,
    )
    framework.main()
