from utils import *


def meson_setup(config, build_dir, installation_dir=None, additional_args=[], reconfigure=True, verbose=True, meson_command="meson"):
    match config.build_type:
        case BuildType.Debug:
            build_type_arg = "--buildtype debug"  # additional --debug parameter is superfluous
        case BuildType.Release:
            build_type_arg = "--buildtype release"
        case BuildType.RelWithDebInfo:
            build_type_arg = "--buidtype debugoptimized"

    installation_dir_arg = "" if installation_dir is None else f"--prefix {installation_dir}"
    additional_args = " ".join(additional_args)
    reconfigure_arg = "--reconfigure" if reconfigure else ""
    command = f"{meson_command} setup {build_type_arg} {installation_dir_arg} {additional_args} {reconfigure_arg} {build_dir}"

    if verbose:
        print(command)
    run_command(command)


def meson_configure(build_dir, options, verbose=True, meson_command="meson"):
    options = " ".join(options)
    command = f"{meson_command} configure {build_dir} {options}"

    if verbose:
        print(command)
    run_command(command)
