#!/bin/sh
find $DUSH_PATH -type f -print0 | xargs -0 dos2unix
