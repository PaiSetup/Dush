import json
import shutil

from dush.utils import *

if is_linux():
    vk_icd_installation_amdgpupro_path = HardcodedPath("/etc/vulkan/icd.d/amd_icd64.json", is_directory=False)
    vk_icd_installation_radv_path = HardcodedPath("/usr/share/vulkan/icd.d/radeon_icd.x86_64.json", is_directory=False)
    vk_icd_dush_path = HardcodedPath(workspace_path / "vk.json", required=False, is_directory=False)

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

    def install_system_amdgpupro_driver():
        install_linux_vulkan_driver(vk_icd_installation_amdgpupro_path.get())

    def install_system_radv_driver():
        install_linux_vulkan_driver(vk_icd_installation_radv_path.get())
