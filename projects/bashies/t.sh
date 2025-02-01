#!/bin/sh

t() (
    if [ "$(basename "$(pwd)")" != "build" ]; then
        mkdir -p build
        cd build || return
    fi

    if [ "$DUSH_IS_LINUX" = 1 ]; then
        extraArgs="-- -j$(nproc)"
    fi

    cmake .. || return 1
    cmake --build . --config Debug $extraArgs || return 1
    ctest -C Debug --verbose || return 1
)
