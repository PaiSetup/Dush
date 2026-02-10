#!/bin/python

import os
import sys
from pathlib import Path

from dush.utils.run_command import run_command


def find_build_and_source_directory():
    cmake_file_name = "CMakeLists.txt"
    build_dir_names = [
        "build",
        "build64",
        "build32",
    ]

    cwd = Path.cwd()
    if str(cwd.name) in build_dir_names and (cwd.parent / cmake_file_name).is_file():
        print(f"Cwd is build dir.")
        return (cwd, cwd.parent)

    if not (cwd / cmake_file_name).is_file():
        print(f"Cannot build - no CMakeLists.txt")
        return None

    build_dir = cwd / "build"
    print(f"Build dir is: {build_dir}")
    build_dir.mkdir(exist_ok=True, parents=True)
    return (build_dir, cwd)


build_dir, source_dir = find_build_and_source_directory()
forwarded_args = " ".join((f'"{x}"' for x in sys.argv[1:]))
command = f"cmake -B {build_dir} -S {source_dir} {forwarded_args}"
run_command(command)
