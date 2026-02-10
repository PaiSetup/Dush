#!/bin/sh

set_ps() {
    PS1="\[\033]0;$TITLEPREFIX:$PWD\007\]\[\033[32m\]\u@\h \[\033[35m\]$MSYSTEM \[\033[33m\]\w\[\033[36m\]$(__git_ps1)\[\033[0m\] $ "
}

PROMPT_COMMAND="set_ps"
