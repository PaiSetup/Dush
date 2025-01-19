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


def get_build_dir(project_dir, config):
    return project_dir / f"build.{config.build_type}"


def get_binary_dir(build_dir):
    return build_dir / "YUViewApp"


# ----------------------------------------------------------- Commands
@command
def qmake(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    source_file = project_dir / "YUView.pro"

    core.qmake(source_file, build_dir, config, qt_path.get(), vc_varsall_path.get())


@command
def compile(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    binary_dir = get_binary_dir(build_dir)
    exe_path = binary_dir / "YUView.exe"

    if is_windows():
        core.compile_with_nmake(
            directory=build_dir,
            vc_varsall_path=vc_varsall_path,
        )
        core.qmake_deploy(qt_path, exe_path)
    else:
        core.compile_with_make(directory=build_dir)
    print(f"Compiled application: {exe_path}")


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
