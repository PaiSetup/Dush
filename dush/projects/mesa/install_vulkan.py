import json
import shlex
import shutil

import dush.core as core
from dush.utils import *

if is_linux():
    vk_icd_installation_amdgpupro_path = HardcodedPath("/etc/vulkan/icd.d/amd_icd64.json", is_directory=False)
    vk_icd_installation_radv_path = HardcodedPath("/usr/share/vulkan/icd.d/radeon_icd.x86_64.json", is_directory=False)
    vk_icd_dush_path = HardcodedPath(workspace_path / "vk.json", required=False, is_directory=False)
    vk_icd_api_version = "1.4.364" # TODO don't hardcode

    def install_linux_vulkan_driver(vk_icd, driver_path_override=None):
        if driver_path_override is not None:
            with open(vk_icd, "r") as file:
                data = json.load(file)
                data["ICD"]["library_path"] = str(driver_path_override)

            with open(vk_icd_dush_path.get(), "w") as file:
                json.dump(data, file, indent=4)

            installed_driver_path = driver_path_override
        else:
            shutil.copy2(vk_icd, vk_icd_dush_path.get())

            with open(vk_icd, "r") as file:
                data = json.load(file)
                installed_driver_path = data["ICD"]["library_path"]

        print(f"Installed Vulkan driver: {installed_driver_path} (via {vk_icd_dush_path.get()})")

    def install_remote_vulkan_driver(binary_dir, driver_name, vk_icd_name, dst_dir):
        """Copy the driver to a remote machine and write an ICD manifest pointing to it.

        The manifest from the build directory is not reused, because it points to the system driver location.
        The switchable graphics layer it declares is skipped, we have no use for it.
        """
        # If the destination directory does not exist, scp silently creates a file in its place instead of failing
        run_command(f"ssh {dst_dir.get_ssh_host()} mkdir -p {shlex.quote(str(dst_dir.get_path()))}")
        core.install(binary_dir, dst_dir, [driver_name], None)

        driver_path = (dst_dir / driver_name).get_path()
        vk_icd_path = (dst_dir / vk_icd_name).get_path()
        vk_icd = json.dumps(
            {
                "file_format_version": "1.0.0",
                "ICD": {
                    "library_path": str(driver_path),
                    "api_version": vk_icd_api_version,
                },
            },
            indent=4,
        )

        # Quoting happens twice: the inner one is for the shell on the remote machine, the outer one for the local shell
        write_command = f"echo {shlex.quote(vk_icd)} > {shlex.quote(str(vk_icd_path))}"
        run_command(f"ssh {dst_dir.get_ssh_host()} {shlex.quote(write_command)}")

        print(f"Installed Vulkan driver: {driver_path} (via {vk_icd_path})")

    def install_system_amdgpupro_driver():
        install_linux_vulkan_driver(vk_icd_installation_amdgpupro_path.get())

    def install_system_radv_driver():
        install_linux_vulkan_driver(vk_icd_installation_radv_path.get())
