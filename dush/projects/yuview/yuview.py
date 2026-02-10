import tempfile
from pathlib import Path

import dush.core as core
from dush.framework import *
from dush.utils import *

# ----------------------------------------------------------- Helpers for commands
is_main = __name__ == "__main__"
project_repositories.load(Path(__file__).parent)

qt_path = EnvPath("QT_PATH", is_directory=True, required=False)
vc_varsall_path = EnvPath("VC_VARSALL_PATH", is_directory=False, required=False)


def get_build_dir(project_dir, config):
    return project_dir / f"build.{config.build_type}"


def get_app_binary_path(build_dir):
    result = build_dir / "YUViewApp/YUView"
    if is_windows():
        result = result.with_suffix(".exe")
    return result


def get_unit_tests_binary_path(build_dir):
    result = build_dir / "YUViewUnitTest/YUViewUnitTest"
    if is_windows():
        result = result.with_suffix(".exe")
    return result


# ----------------------------------------------------------- Commands
@command
def qmake(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    source_file = project_dir / "YUView.pro"
    args = [
        "'CONFIG+=UNITTESTS debug'",
    ]

    core.qmake(source_file, build_dir, config, args, qt_path.get(), vc_varsall_path.get())


@command
def compile(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)

    # Remove unit tests executable to ensure it's recompiled. The .pro file is missing dependency on the YUViewLib.
    unit_test_path = get_unit_tests_binary_path(build_dir)
    unit_test_path.unlink(missing_ok=True)

    if is_windows():
        core.compile_with_nmake(
            directory=build_dir,
            vc_varsall_path=vc_varsall_path,
        )
        core.qmake_deploy(qt_path, exe_path)
    else:
        core.compile_with_make(directory=build_dir)
    print(f"Compiled application: {get_app_binary_path(build_dir)}")


@command
def run(config="", perform_compilation=False):
    config = interpret_arg(config, BuildConfig, "config")
    perform_compilation = interpret_arg(perform_compilation, bool, "perform_compilation")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)

    if perform_compilation:
        compile(config)

    command = str(get_app_binary_path(build_dir))
    run_command(command)


@command
def run_unit_tests(config="", perform_compilation=False, test_pattern=""):
    config = interpret_arg(config, BuildConfig, "config")
    perform_compilation = interpret_arg(perform_compilation, bool, "perform_compilation")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)

    if perform_compilation:
        compile(config)

    command = str(get_unit_tests_binary_path(build_dir))
    if test_pattern:
        command = f"{command} --gtest_filter={test_pattern}"
    run_command(command)


# ----------------------------------------------------------- Main procedure
if is_main:
    BuildConfig.configure(
        [Compiler.VisualStudio],
        [Bitness.x64],
        [BuildType.Debug, BuildType.Release],
        Compiler.VisualStudio,
        Bitness.x64,
        BuildType.Release,
    )
    framework.main()
