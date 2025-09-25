#!/bin/sh

if [ "$DUSH_IS_LINUX" = 1 ]; then
    alias p="ps aux --forest"
else
    alias p="ps -W"
fi

alias pp="p | less"

pe() {
    pid="$1"
    if ! [ -f /proc/$pid/environ ]; then
        pid="$(pgrep -x $1)"
        res=$?
        if [ $? != 0 ]; then
            echo "ERROR: PID of $1 could not be found" >&2
            return $res
        fi
        count="$(echo "$pid" | wc -l)"
        if [ "$count" != 1 ]; then
            echo "ERROR: $count $1 processes running. Choose one. PIDs: $(echo "$pid" | tr '\n' ' ')" >&2
            return 1
        fi
        if ! [ -f /proc/$pid/environ ]; then
            echo "ERROR: PID of $1 could not be found" >&2
            return 1
        fi
    fi

    cat /proc/$pid/environ | tr '\0' '\n'
}
