import enum
import random
from pathlib import Path

from dush.framework import *
from dush.utils import *

# ----------------------------------------------------------- Helpers for commands
is_main = __name__ == "__main__"
project_repositories.load(Path(__file__).parent)


class TaskType(enum.Enum):
    Persistent = "persistent"
    FailQuickly = "fail_quickly"

    @staticmethod
    def interpret_arg(arg, name):
        arg = arg.lower()
        if arg in ["p", "persistent"]:
            return TaskType.Persistent
        elif arg in ["f", "fail_quickly"]:
            return TaskType.FailQuickly
        else:
            raise ValueError(f"Invalid {name}: {arg}. Valid types are: {TaskType.Persistent.value}, {TaskType.FailQuickly.value}")


# ----------------------------------------------------------- Commands
@command
def compile():
    get_project_dir()
    run_command("go build .")


@command
def run_server(perform_compilation=True):
    perform_compilation = interpret_arg(perform_compilation, bool, "perform_compilation")

    get_project_dir()

    if perform_compilation:
        compile()

    run_command("go run . serve")


@command
def sched(task_type=TaskType.FailQuickly):
    task_type = interpret_arg(task_type, TaskType, "task_type")

    get_project_dir()

    args = ""
    args += " --display h"
    match task_type:
        case TaskType.Persistent:
            args += " --max-subsequent-failures -1"
        case TaskType.FailQuickly:
            args += " --max-subsequent-failures 0"
        case _:
            raise ValueError(f"Invalid task type: {task_type}")
    args += f" --friendly-name {random.randint(0, 1000):04d}"
    args += " -- bash test_scripts/test_script.sh"

    run_command(f"go run . schedule{args}")


@command
def list_tasks(perform_compilation=True, *args):
    perform_compilation = interpret_arg(perform_compilation, bool, "perform_compilation")

    get_project_dir()

    if perform_compilation:
        compile()

    run_command(f"go run . list {' '.join(args)}")


# ----------------------------------------------------------- Main procedure
if is_main:
    framework.main()
