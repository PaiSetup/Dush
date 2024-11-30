from framework import *
from utils.paths import EnvPath
from pathlib import Path
import os
import re

# This variable points to a directory which contains all of the developer's work projects.
workspace_path = EnvPath("DUSH_WORKSPACE", lazy_resolve=False)

class ProjectRepository:
    """
    This structure describes a remote repository that can be cloned and its metadata.
    It doesn't point to a specific cloned directory, but gives information on how to
    recognize a clone directory.
    """
    def __init__(self, root_name_prefix, url, dir_suffix, dev_branch):
        self.root_name_prefix = root_name_prefix
        self.url = url
        self.dir_suffix = dir_suffix
        self.dev_branch = dev_branch
        self.dev_branch_local = f"origin/{dev_branch}"

class ProjectRepositories:
    """
    Storage for ProjectRepository structures
    """
    def __init__(self):
        self._repositories = dict()
        self._main_repository_name = None

    def add(self, name, repository, is_main):
        name = name.lower()
        if name in self._repositories:
            raise KeyError(f"Duplicate repository name: \"{name}\".")
        self._repositories[name] = repository
        if is_main:
            self._main_repository_name = name

    def get_main(self):
        return self._repositories[self._main_repository_name]

    def get(self, name=None):
        if name is None:
            name = self._derive_name()
            if name is None:
                available_names = ", ".join(self._repositories.keys())
                raise ValueError(f"Could not derive ProjectRepository from cwd. Specify one of [{available_names}].")

        name = name.lower()
        try:
            return self._repositories[name]
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

project_repositories = ProjectRepositories()

class IncorrectEnvironmentError(Exception):
    pass

class IncorrectProjectDirectory(Exception):
    pass

def get_project_dir(root_name_prefix=None, suffix=None, do_chdir=True):
    # Get arguments from current directory if not specified
    if suffix is None:
        suffix = project_repositories.get_main().dir_suffix
    if root_name_prefix is None:
        root_name_prefix = project_repositories.get_main().root_name_prefix

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
    new_cwd = workspace_path / subdir / suffix

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
        suffix = project_repositories.get_main().dir_suffix
    if root_name_prefix is None:
        root_name_prefix = project_repositories.get_main().root_name_prefix

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
