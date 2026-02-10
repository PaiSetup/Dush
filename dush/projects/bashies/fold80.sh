#!/bin/sh

fold80() (
    if [ -z "$1" ] ; then
        echo "ERROR: specify text in cmdline arg"
    fi

    echo "--------------"
    echo "$1" | tr "\n" " " | fold -w 80 -s
    echo
    echo "--------------"
)
