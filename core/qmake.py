from utils.build_config import BuildType
from utils.os_function import is_windows, windows_only
from utils.run_command import run_command, wrap_command_with_vcvarsall


def get_qt_binary(binary, qt_path):
    if qt_path is not None:
        binary = f"{qt_path}/bin/{binary}"
    if is_windows():
        binary += ".exe"
    return binary


def qmake(source_file, build_dir, config, qt_path=None, vc_varsall_path=None):
    qmake_path = get_qt_binary("qmake", qt_path)
    command = f"{qmake_path} {source_file}"

    if config.build_type == BuildType.Debug:
        command += " CONFIG+=debug"  # TODO is this really a QT thing or a YUView thing?

    if is_windows():
        if vc_varsall_path is not None:
            command = wrap_command_with_vcvarsall(vc_varsall_path, command)

    build_dir.mkdir(parents=True, exist_ok=True)
    run_command(command, cwd=build_dir)


@windows_only
def qmake_deploy(qt_path, exe_path):
    deploy_path = get_qt_binary("windeployqt", qt_path)
    qtpaths_path = get_qt_binary("qtpaths", qt_path)
    command = f"{deploy_path} --qtpaths {qtpaths_path} {exe_path}"
    run_command(command)
