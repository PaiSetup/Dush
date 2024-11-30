from utils import run_command
from utils.os_function import windows_only, linux_only
from utils.build_config import Compiler, BuildType, Bitness
from pathlib import Path

class IncorrectGitWorkspaceError(Exception):
    pass

@windows_only
def generate_config_options(config):
    options = ""
    if config.compiler == Compiler.VisualStudio:
        options += f' -G "Visual Studio 17 2022"'
        if config.bitness == Bitness.x64:
            options += " -A x64 -T host=x64"
        elif config.bitness == Bitness.x32:
            options += " -A Win32 -T host=x86"
        else:
            raise KeyError("Unsupported bitness")
    elif config.compiler == Compiler.Ninja:
        options += " -G Ninja"
    else:
        raise KeyError("Unsupported bitness")
    return options


def setup_git_exclude_for_build_directory(build_dir):
    def find_exclude_file(git_dir):
        if git_dir.is_dir():
            # We are in a normal git repository with a .git directory
            return git_dir / "info/exclude"
        elif git_dir.is_file():
            # We are in a submdoule with a .git file. It contains a path
            # to the git directory of this module.
            with open('.git', 'r') as file:
                for line in file.readlines():
                    prefix = "gitdir: "
                    if line.startswith(prefix):
                        module_git_dir = line[len(prefix):]
                        module_git_dir = module_git_dir.strip()
                        module_git_dir = git_dir.parent / module_git_dir
                        module_git_dir = module_git_dir.resolve()
                        return find_exclude_file(module_git_dir)
            raise IncorrectGitWorkspaceError(f"{git_dir} does not contain gitdir line")
        else:
            raise IncorrectGitWorkspaceError(f"{git_dir} does not exist")

    # Get the path to exclude file
    top_level_dir = run_command("git rev-parse --show-toplevel", return_stdout=True, print_stdout=False)
    top_level_dir = top_level_dir.strip()
    top_level_dir = Path(top_level_dir)
    git_dir = top_level_dir / ".git"
    exclude_file = find_exclude_file(git_dir)

    # Gather existing lines in the exclude file
    with open(exclude_file, "r") as file:
        existing_lines = file.read()
        existing_lines = existing_lines.split('\n')

    # Add build dir if neccessary
    new_exclude = build_dir.relative_to(top_level_dir)
    new_exclude = str(new_exclude)
    if new_exclude not in existing_lines:
        with open(exclude_file, "w") as file:
            for line in existing_lines:
                file.write(f'{line}\n')
            file.write(f'{new_exclude}\n')


def cmake(config, build_dir, source_dir,
          additional_cmake_options : list,
          additional_paths : list,
          additional_env : dict,
          *,
          append_config_options = True,
          verbose = True):
    build_dir.mkdir(exist_ok=True)

    command = "cmake"
    command += f" -B {build_dir} -S {source_dir}"
    command += " -Wno-dev "
    command += ' '.join(additional_cmake_options)
    if append_config_options:
        command += generate_config_options(config)

    if verbose:
        print(command)

    run_command(command, env=additional_env, paths=additional_paths)

    setup_git_exclude_for_build_directory(build_dir)