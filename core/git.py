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


def checkout(branch):
    run_command(f"git checkout {branch}")


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
