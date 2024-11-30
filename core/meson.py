from utils import *

def meson(config, build_dir, source_dir,
          additional_meson_options,
          reconfigure = True,
          verbose = True):
    match config.build_type:
        case BuildType.Debug:
            build_type_arg = "--buildtype debug" # additional --debug parameter is superfluous
        case BuildType.Release:
            build_type_arg = "--buildtype release"
        case BuildType.RelWithDebInfo:
            build_type_arg = "--buidtype debugoptimized"

    command = f"meson setup {additional_meson_options} {build_type_arg} --prefix {source_dir} {build_dir}"
    if reconfigure:
        command += " --reconfigure"

    if verbose:
        print(command)

    run_command(command)
