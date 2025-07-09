from utils import *
from framework import *
import core

repo = project_repositories.get_main()
has_submodules = repo.has_git_submodules
has_clean_command = framework.get_command("clean") is not None

@command_conditional(has_clean_command)
def clean_all():
    clean_command = framework.get_command("clean")
    for config in BuildConfig.all_permutations():
        clean_command(config)

@command
def top(clean_all=False):
    clean_all = interpret_arg(clean_all, bool, "clean_all")

    get_project_dir()
    upstream_dev_branch_local = f"origin/{repo.upstream_dev_branch}"

    core.fetch(repo.upstream_dev_branch)
    core.checkout(upstream_dev_branch_local)
    if has_submodules:
        core.update_submodules()
    if clean_all:
        if not has_clean_command:
            raise ValueError("Cannot perform clean, because 'clean' command is not defined.")
        clean_all()

@command
def rebase(update_submodules=True):
    update_submodules = interpret_arg(update_submodules, bool, "update_submodules")

    get_project_dir()
    upstream_dev_branch_local = f"origin/{repo.upstream_dev_branch}"

    core.fetch(repo.upstream_dev_branch)
    core.rebase(upstream_dev_branch_local)
    if update_submodules:
        core.update_submodules()

@command_conditional(has_submodules)
def update_submodules():
    get_project_dir()
    core.update_submodules()

@command
def cherrypick_remote_branch(branch):
    get_project_dir()

    branch_local = f"origin/{branch}"

    core.fetch(branch)
    core.cherrypick(branch_local)

@command
def checkout_remote_branch(branch):
    get_project_dir()

    branch_local = f"origin/{branch}"

    core.fetch(branch)
    core.checkout(branch_local)
    core.update_submodules()
