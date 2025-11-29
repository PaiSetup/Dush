import os
import re
from pathlib import Path

from framework import *
from utils import *


class DushProject:
    def __init__(self, path):
        self.path = Path(path)


class DushProjectRepository:
    def __init__(self):
        self._projects = dict()

    def load_all(self):
        for config_file in dush_path.get().glob("projects/**/config.ini"):
            project_dir = Path(config_file).parent
            self.load(project_dir)

    def load(self, project_dir):
        project = DushProject(project_dir)

        # Read config
        config_file_path = project_dir / "config.ini"
        with open(config_file_path, "r") as file:
            for line in file:
                # Extract key/value pair
                equals_sign_pos = line.find("=")
                if equals_sign_pos == -1:
                    continue
                key = line[:equals_sign_pos].strip()
                value = line[equals_sign_pos + 1 :].strip()

                # Set as attributes of the project
                setattr(project, key, value)

        # Add the project
        name = project.name.lower()
        if name in self._projects:
            raise KeyError(f'Duplicate project name: "{name}".')
        self._projects[name] = project
        return project

    def get_main(self):
        match len(self._projects):
            case 0:
                raise KeyError("No projects in the repository.")
            case 1:
                return next(iter(self._projects.values()))
            case _:
                raise KeyError("Too many projects in the repository, cannot select main.")

    def get(self, name=None):
        if name is None:
            name = self._derive_name()
            if name is None:
                available_names = ", ".join(self._projects.keys())
                raise ValueError(f"Could not derive DushProject from cwd. Specify one of [{available_names}].")

        name = name.lower()
        try:
            return self._projects[name]
        except:
            raise ValueError("")

    def _get_current_project_dir_name(self):
        try:
            path = Path.cwd().relative_to(workspace_path.get())
        except ValueError:
            return None
        if path is None or path == ".":
            return None
        return path.parts[0]

    def _derive_name(self):
        dir_name = self._get_current_project_dir_name()
        if dir_name is None:
            return None

        matcher = re.search("^([a-zA-z]+)", dir_name)
        if matcher is None:
            return None

        return matcher.groups()[0]


# TODO rename to dush_projects
project_repositories = DushProjectRepository()


class IncorrectEnvironmentError(Exception):
    pass


class IncorrectProjectDirectory(Exception):
    pass


def get_project_dir(root_name_prefix=None, suffix=None, do_chdir=True):
    # Get arguments from current directory if not specified
    if suffix is None:
        suffix = project_repositories.get_main().dir_inside_root
    if root_name_prefix is None:
        root_name_prefix = project_repositories.get_main().name

    if framework.get_framework_args().project_dir_force is not None:
        root_name_prefix = framework.get_framework_args().project_dir_force

    cwd = Path(os.getcwd())

    # Get project's root directory
    try:
        subdir = cwd.relative_to(workspace_path.get())
    except ValueError:
        raise IncorrectProjectDirectory(f"not a {root_name_prefix} repo")
    try:
        subdir = subdir.parts[0]
    except IndexError:
        raise IncorrectProjectDirectory(f"not a {root_name_prefix} repo")

    # Verify the name of project root directory
    if not re.match(f"{root_name_prefix}[0-9]*$", str(subdir)):
        raise IncorrectProjectDirectory(f"not a {root_name_prefix} repo")

    # Compose the project path
    new_cwd = workspace_path / subdir
    if suffix and suffix != ".":
        new_cwd = new_cwd / suffix

    # cd to the path if requested
    if do_chdir:
        try:
            os.chdir(new_cwd)
        except FileNotFoundError:
            raise IncorrectProjectDirectory(f"invalid {root_name_prefix} repo")

    # Return the path
    return new_cwd


def get_project_dirs(root_name_prefix=None, suffix=None):
    # Get arguments from current directory if not specified
    if suffix is None:
        suffix = project_repositories.get_main().dir_inside_root
    if root_name_prefix is None:
        root_name_prefix = project_repositories.get_main().name

    # Get overridden arguments for cmdline
    if framework.get_framework_args().project_dir_force is not None:
        root_name_prefix = framework.get_framework_args().project_dir_force

    # Return directories matching the name pattern
    name_pattern = rf"{root_name_prefix}[0-9]*$"
    result = []
    for name in os.listdir(workspace_path.get()):
        if not re.match(name_pattern, name):
            continue

        project_dir = workspace_path / name / suffix
        if not project_dir.is_dir():
            raise IncorrectProjectDirectory(f"invalid {root_name_prefix} repo")

        result.append(project_dir)
    return result
