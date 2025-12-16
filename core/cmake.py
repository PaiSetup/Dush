from pathlib import Path

from core.git import add_transient_gitignore
from utils import Stdout, run_command
from utils.build_config import Bitness, Compiler
from utils.os_function import is_linux


class IncorrectGitWorkspaceError(Exception):
    pass


def generate_config_options(config):
    def append_linux_single_config_32bit_options(config, options):
        if is_linux() and config.bitness == Bitness.x32:
            options += " -DCMAKE_C_FLAGS=-m32 -DCMAKE_CXX_FLAGS=-m32"
        return options

    options = ""
    match config.compiler:
        case Compiler.VisualStudio:
            options += f' -G "Visual Studio 17 2022"'
            if config.bitness == Bitness.x64:
                options += " -A x64 -T host=x64"
            elif config.bitness == Bitness.x32:
                options += " -A Win32 -T host=x86"
            else:
                raise KeyError("Unsupported bitness")
        case Compiler.Ninja:
            options += " -G Ninja"
            options += f" -DCMAKE_BUILD_TYPE={str(config.build_type)}"
            options = append_linux_single_config_32bit_options(config, options)
        case Compiler.Makefiles:
            options += ' -G "Unix Makefiles"'
            options += f" -DCMAKE_BUILD_TYPE={str(config.build_type)}"
            options = append_linux_single_config_32bit_options(config, options)
        case _:
            raise KeyError("Unsupported compiler")
    return options


def cmake(
    config,
    build_dir,
    source_dir,
    additional_cmake_options: list = [],
    additional_paths: list = [],
    additional_env: dict = {},
    additional_ld_library_paths: list = [],
    *,
    append_config_options=True,
    verbose=True,
):
    build_dir.mkdir(exist_ok=True)

    command = "cmake"
    command += f" -B {build_dir} -S {source_dir}"
    command += " -Wno-dev "
    command += " ".join(additional_cmake_options)
    if append_config_options:
        command += generate_config_options(config)

    if verbose:
        print(command)

    run_command(command, env=additional_env, paths=additional_paths, ld_library_paths=additional_ld_library_paths)

    add_transient_gitignore(build_dir)
