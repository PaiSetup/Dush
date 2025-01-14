from utils.run_command import run_command, wrap_command_with_vcvarsall
from utils.build_config import BuildType
from utils.os_function import windows_only

@windows_only
def qmake(source_file, build_dir, config, qt_path, vc_varsall_path=None):
    command = f"{qt_path}/bin/qmake.exe {source_file}"
    if config.build_type == BuildType.Debug:
        command += " CONFIG+=debug"
    if vc_varsall_path is not None:
        command = wrap_command_with_vcvarsall(vc_varsall_path, command)
    build_dir.mkdir(parents=True, exist_ok=True)
    run_command(command, cwd=build_dir)

@windows_only
def qmake_deploy(qt_path, exe_path):
    command = f"{qt_path}/bin/windeployqt.exe --qtpaths {qt_path}/bin/qtpaths.exe {exe_path}"
    run_command(command)
