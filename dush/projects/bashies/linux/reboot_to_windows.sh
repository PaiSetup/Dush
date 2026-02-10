#!/bin/sh

reboot_to_windows() (
    impl() {
        windows_title="$(sudo grep -i "menuentry 'windows" /boot/grub/grub.cfg | cut -d"'" -f2)"
        if [ $? != 0 ]; then
            error="failed to query grub menuentry for Windows."
            return 1
        fi
        if [ -z "$windows_title" ]; then
            error="no menuentry for Windows was found."
            return 1
        fi
        if [ "$(echo "$windows_title" | wc -l)" != 1 ]; then
            error="too many menuentries for Windows were found."
            return 1
        fi
        echo "Windows menuentry is: $windows_title"

        echo "Executing grub-reboot..."
        sudo grub-reboot "$windows_title" || return 1
        if [ $? != 0 ]; then
            error="failed execute grub-reboot."
            return 1
        fi

        echo "Rebooting..."
        sudo reboot || return 1
        if [ $? != 0 ]; then
            error="failed execute reboot."
            return 1
        fi
    }

    impl
    if [ $? != 0 ]; then
        echo "❌ Error" "Could not reboot to Windows: $error"
        return 1
    fi
)
