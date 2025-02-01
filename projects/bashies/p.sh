#!/bin/sh

if [ "$DUSH_IS_LINUX" = 1 ]; then
    alias p="ps aux --forest"
else
    alias p="ps -W"
fi

alias pp="p | less"
