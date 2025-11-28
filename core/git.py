from pathlib import Path

from utils import CommandError, RaiiChdir, Stdout, run_command


class GithubNotAllowed(Exception):
    pass


github_error = None
try:
    from github import Github
except ImportError:
    github_error = GithubNotAllowed("PyGithub library is not installed")


class IncorrectProjectDirectory(Exception):
    pass


def add_transient_gitignore(path_to_ignore):
    def find_exclude_file(git_dir):
        if git_dir.is_dir():
            # We are in a normal git repository with a .git directory
            return git_dir / "info/exclude"
        elif git_dir.is_file():
            # We are in a submodule with a .git file. It contains a path
            # to the git directory of this module.
            with open(".git", "r") as file:
                for line in file.readlines():
                    prefix = "gitdir: "
                    if line.startswith(prefix):
                        module_git_dir = line[len(prefix) :]
                        module_git_dir = module_git_dir.strip()
                        module_git_dir = git_dir.parent / module_git_dir
                        module_git_dir = module_git_dir.resolve()
                        return find_exclude_file(module_git_dir)
            raise IncorrectGitWorkspaceError(f"{git_dir} does not contain gitdir line")
        else:
            raise IncorrectGitWorkspaceError(f"{git_dir} does not exist")

    # Get the path to exclude file
    top_level_dir = run_command("git rev-parse --show-toplevel", stdout=Stdout.return_back()).stdout
    top_level_dir = top_level_dir.strip()
    top_level_dir = Path(top_level_dir)
    git_dir = top_level_dir / ".git"
    exclude_file = find_exclude_file(git_dir)

    # Gather existing lines in the exclude file
    with open(exclude_file, "r") as file:
        existing_lines = file.read()
        existing_lines = existing_lines.split("\n")

    # Add build dir if neccessary
    path_to_ignore = path_to_ignore.relative_to(top_level_dir)
    path_to_ignore = str(path_to_ignore)
    if path_to_ignore not in existing_lines:
        with open(exclude_file, "w") as file:
            for line in existing_lines:
                file.write(f"{line}\n")
            file.write(f"{path_to_ignore}\n")


def reset_repo(directory="."):
    with RaiiChdir(directory) as chdir:
        if not chdir.success:
            raise IncorrectProjectDirectory(f"Could not enter {directory}")
        print(f"Resetting git state of {chdir.cwd}")
        run_command("git reset --hard")
        run_command("git clean -fxd")


def update_submodules(directory=".", recursive=True):
    recursive_option = " --recursive" if recursive else ""
    run_command(f"git submodule update{recursive_option} --init {directory}")


def fetch(branch="master"):
    run_command(f"git fetch origin {branch} --prune --recurse-submodules=no")


def checkout(branch, force=False):
    force_option = " -f" if force else ""
    run_command(f"git checkout{force_option} {branch}")


def cherrypick(commit):
    run_command(f"git cherry-pick {commit}")


def rebase(branch, until_argument=""):
    """
    until_argument can be used for situation when we don't want to rebase to a latest commit. But rather put a boundary like --until=10hours, meaning
    latest commit merged 10 hours ago or earlier. Useful for example when we know there's an ongoing regression.
    """
    if until_argument:
        commit = run_command(f"git log {branch} --first-parent --until={until_argument} -1 --format=%H", stdout=Stdout.return_back()).stdout
        commit = commit.strip()
    else:
        commit = branch
    run_command(f"git rebase {commit}")


def gc():
    run_command("git gc")


def find_baseline_commit(branch):
    return run_command(f"git merge-base HEAD origin/{branch}", stdout=Stdout.return_back()).stdout


def get_branch():
    try:
        branch = run_command("git branch --no-color --show-current", stdout=Stdout.return_back()).stdout
    except CommandError:
        raise IncorrectProjectDirectory("Not a git repo")
    if branch == "":
        return None
    else:
        return branch.strip()


def get_commit_hash(characters=None):
    commit_hash = run_command("git rev-parse HEAD", stdout=Stdout.return_back()).stdout
    commit_hash = commit_hash.strip()
    if characters is not None:
        commit_hash = commit_hash[:characters]
    return commit_hash
