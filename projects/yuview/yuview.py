from utils import *
from framework import *
import core
import tempfile

# ----------------------------------------------------------- Helpers for commands
is_main = __name__ == "__main__"
repo = ProjectRepository(
    root_name_prefix = "yuview",
    url = "https://github.com/IENT/YUView",
    dir_suffix = ".",
    dev_branch = "main",
)
project_repositories.add(repo.root_name_prefix, repo, is_main)

qt_path = EnvPath("QT_PATH", is_directory=True)
vc_varsall_path = EnvPath("VC_VARSALL_PATH", is_directory=False)

def get_build_dir(project_dir, config):
    return project_dir / f"build.{config.build_type}"

def get_binary_dir(build_dir):
    return build_dir / "YUViewApp"

# ----------------------------------------------------------- Commands
@command
def qmake(config = ""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    source_file = project_dir / "YUView.pro"

    core.qmake(source_file, build_dir, config, qt_path, vc_varsall_path)

@command
def compile(config = ""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    binary_dir = get_binary_dir(build_dir)
    exe_path = binary_dir / "YUView.exe"

    core.compile_with_nmake(
        directory=build_dir,
        vc_varsall_path=vc_varsall_path,
    )
    core.qmake_deploy(qt_path, exe_path)
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
