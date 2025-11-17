#!/bin/sh

awesome_path="$1"
test_display="$2"
use_default_config="$3"

Xephyr -br -ac -noreset -screen 800x600 $test_display &
pid_xephyr=$!

default_config_arg=""
if [ "$use_default_config" = "1" ]; then
    default_config_arg="-c /etc/xdg/awesome/rc.lua"
fi
echo ">>>$use_default_config<<<   >>>$default_config_arg<<<"

(
    export DISPLAY=$test_display
    sleep 1
    exec "$awesome_path" $default_config_arg &
)
pid_wm=$!

echo "Testing $awesome_path (PID: $pid_wm) inside $(which Xephyr) ($pid_xephyr) on X display $test_display"
echo "Press enter to stop."
read -r _
kill -9 $pid_wm
kill $pid_xephyr
