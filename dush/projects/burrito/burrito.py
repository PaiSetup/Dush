import tempfile
from pathlib import Path

import dush.core as core
from dush.framework import *
from dush.utils import *

# ----------------------------------------------------------- Helpers for commands
is_main = __name__ == "__main__"
project_repositories.load(Path(__file__).parent)


def get_build_dir(project_dir):
    return project_dir / "build"


def get_executable(build_dir):
    return build_dir / "burrito.x86_64"


def get_godot_binary_dir(project_dir):
    return project_dir / "godot_bin"


def get_godot_cli(godot_binary_dir):
    return godot_binary_dir / "godot_cli"


def get_godot_gui(godot_binary_dir):
    return godot_binary_dir / "godot_gui"


# ----------------------------------------------------------- Commands

import os


@linux_only
def download_file(url, destination_path):
    command = f"wget -q {url} -O {destination_path}"
    run_command(command)


@linux_only
def unzip(zip_path, destination_dir_path, directory_inside_zip=None):
    directory_inside_zip_arg = f"{directory_inside_zip}/*" if directory_inside_zip else ""

    destination_dir_path.mkdir(parents=True, exist_ok=True)
    command = f"unzip -o {zip_path} {directory_inside_zip_arg} -d {destination_dir_path}"
    run_command(command)

    if directory_inside_zip:
        extracted_dir = destination_dir_path / directory_inside_zip
        for extracted_file in extracted_dir.iterdir():
            renamed_extracted_file = destination_dir_path / extracted_file.name
            extracted_file.rename(renamed_extracted_file)
        extracted_dir.rmdir()


@linux_only
def download_and_unpack_zip(url, destination_dir_path, directory_inside_zip=None):
    destination_dir_path.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination_dir_path, prefix="dush_tmp_", suffix=".zip") as f:
        f.close()
        download_file(url, f.name)
        unzip(f.name, destination_dir_path, directory_inside_zip)
        os.remove(f.name)


@command
def download_build_dependencies():
    godot_version = "3.3.2"

    project_dir = get_project_dir()
    bin_dir = get_godot_binary_dir(project_dir)
    core.add_transient_gitignore(bin_dir)
    godot_cli = get_godot_cli(bin_dir)
    godot_gui = get_godot_gui(bin_dir)

    # Download headless Godot
    url = f"https://github.com/godotengine/godot/releases/download/{godot_version}-stable/Godot_v{godot_version}-stable_linux_headless.64.zip"
    download_and_unpack_zip(url, bin_dir)
    (bin_dir / f"Godot_v{godot_version}-stable_linux_headless.64").rename(godot_cli)

    # Download GUI Godot
    url = f"https://github.com/godotengine/godot/releases/download/{godot_version}-stable/Godot_v{godot_version}-stable_x11.64.zip "
    download_and_unpack_zip(url, bin_dir)
    (bin_dir / f"Godot_v{godot_version}-stable_x11.64").rename(godot_gui)

    # Download export templates for godot
    url = f"https://github.com/godotengine/godot/releases/download/{godot_version}-stable/Godot_v{godot_version}-stable_export_templates.tpz"
    templates_dir = Path(os.getenv("HOME")) / f".local/share/godot/templates/{godot_version}.stable"
    download_and_unpack_zip(url, templates_dir, directory_inside_zip="templates")


@command
def compile(compile_burrito_fg=True, compile_taco_parser=True, compile_gui=True):
    compile_burrito_fg = interpret_arg(compile_burrito_fg, bool, "compile_burrito_fg")
    compile_taco_parser = interpret_arg(compile_taco_parser, bool, "compile_taco_parser")
    compile_gui = interpret_arg(compile_gui, bool, "compile_gui")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir)
    executable = get_executable(build_dir)
    godot_bin_dir = get_godot_binary_dir(project_dir)
    godot_cli = get_godot_cli(godot_bin_dir)

    if compile_burrito_fg:
        run_command("cargo build --release", cwd=project_dir / "burrito-fg")
    if compile_taco_parser:
        run_command("cargo build --release", cwd=project_dir / "taco_parser")
    if compile_gui:
        build_dir.mkdir(exist_ok=True)
        run_command(f"{godot_cli} --export Linux/X11")
        run_command(f"chmod +x {executable}")


@command
def run(perform_compilation=False):
    perform_compilation = interpret_arg(perform_compilation, bool, "perform_compilation")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir)
    executable = get_executable(build_dir)

    if perform_compilation:
        compile()

    run_command(str(executable))


@command
def open_in_godot():
    project_dir = get_project_dir()
    godot_bin_dir = get_godot_binary_dir(project_dir)
    godot_gui = get_godot_gui(godot_bin_dir)

    run_command(f"{godot_gui} project.godot", stdout=Stdout.ignore(), stderr=Stdout.ignore())


# ----------------------------------------------------------- Main procedure
if is_main:
    BuildConfig.configure(
        [Compiler.Makefiles],
        [Bitness.x64],
        [BuildType.Debug, BuildType.Release],
        Compiler.Makefiles,
        Bitness.x64,
        BuildType.Debug,
    )
    framework.main()
