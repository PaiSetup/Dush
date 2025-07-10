#!/bin/sh

dush_init_project mesa

if [ "$DUSH_IS_LINUX" = 1 ]; then
    export VK_ICD_FILENAMES="$DUSH_WORKSPACE/vk.json"
fi
