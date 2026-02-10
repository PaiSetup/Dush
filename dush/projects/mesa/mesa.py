from pathlib import Path

import dush.core as core
from dush.framework import *
from dush.projects.mesa.install_vulkan import (
    install_linux_vulkan_driver,
    install_system_radv_driver,
)
from dush.utils import *

"""
Useful resources about building Mesa:
    https://docs.mesa3d.org/install.html
    https://docs.mesa3d.org/meson.html
    https://gist.github.com/Venemo/a9483106565df3a83fc67a411191edbd?permalink_comment_id=3951924
    https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/meson.build

Install dependencies with sudo apt-get build-dep mesa

Libdrm version might be too low. Build it locally: http://www.linuxfromscratch.org/blfs/view/svn/x/libdrm.html
"""

# Ubuntu 24.04 has Meson 0.61.2-1 and Mesa requres higher... Download Meson manually from
# Github https://github.com/mesonbuild/meson and point to it with this variable.
meson_path = EnvPath("MESON_PATH", is_directory=False, required=True)

# ----------------------------------------------------------- Helpers for commands
is_main = __name__ == "__main__"
project_repositories.load(Path(__file__).parent)


def get_debug_options(config):
    if config.build_type == BuildType.Debug:
        return ["-Ddebug=true", "-Doptimization=0"]
    else:
        return ["-Ddebug=false", "-Doptimization=3"]


def get_build_dir(project_dir, config: BuildConfig):
    build_type = str(config.build_type).lower()
    dir_name = f"build.{build_type}.x64"
    return project_dir / dir_name


def get_driver_path(installation_dir):
    return installation_dir / "lib/x86_64-linux-gnu/libvulkan_radeon.so"


def get_vk_icd_json_path(installation_dir):
    return installation_dir / "share/vulkan/icd.d/radeon_icd.x86_64.json"


def get_installation_dir(build_dir):
    return build_dir / "install"


# ----------------------------------------------------------- Commands
@command
def meson(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    installation_dir = get_installation_dir(build_dir)

    # Hardcoded for radv. Add configuration if needed.
    mesa_args = [
        "-Dgallium-drivers=",
        "-Dgallium-rusticl=false",
        "-Dtools=",
        "-Dvulkan-drivers=amd",
        "-Dvideo-codecs=all",
        "-Dllvm=disabled",
    ] + get_debug_options(config)

    core.meson_setup(config, build_dir, installation_dir, mesa_args, meson_command=meson_path)
    core.meson_configure(
        build_dir, mesa_args, meson_command=meson_path
    )  # This is needed when changing mesa_args. Shouldn't meson setup --reconfigure handle that?


@command
def compile(config=""):
    config = interpret_arg(config, BuildConfig, "config")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)

    core.compile_with_ninja("", build_dir)


@command
def install(config="", perform_compilation=True):
    config = interpret_arg(config, BuildConfig, "config")
    perform_compilation = interpret_arg(perform_compilation, bool, "perform_compilation")

    project_dir = get_project_dir()
    build_dir = get_build_dir(project_dir, config)
    installation_dir = get_installation_dir(build_dir)

    if perform_compilation:
        core.compile_with_ninja("install", build_dir)

    # Hardcoded for radv. Add configuration if needed.
    vk_icd_path = get_vk_icd_json_path(installation_dir)
    install_linux_vulkan_driver(vk_icd_path)


@command
def uninstall():
    # Hardcoded for radv. Add configuration if needed.
    install_system_radv_driver()


# ----------------------------------------------------------- Main procedure
if is_main:
    BuildConfig.configure(
        [Compiler.Ninja],
        [Bitness.x64],
        [BuildType.Debug, BuildType.Release],
        Compiler.Ninja,
        Bitness.x64,
        BuildType.Debug,
    )
    framework.main()
