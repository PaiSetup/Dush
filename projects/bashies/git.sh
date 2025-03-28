#!/bin/sh

alias status="git status"

log() (
    git log --graph --pretty="format:%C(auto,yellow)%H %C(auto,green)%<(20,trunc)%aN %C(auto,cyan)%<(15,trunc)%cr %C(auto,reset)%s %C(auto)%d" "$@"
)

logd() (
    a="%Y-%m-%d    %H:%M:%S"
    git log --graph --pretty="format:%C(auto,yellow)%H %C(auto,green)%<(20,trunc)%aN %C(auto,cyan)%<(45,trunc)%cd %C(auto,reset)%s %C(auto)%d" --date=format:"$a" "$@"
)

logac() (
    divider='%C(auto,red) | '
    hash='%C(auto,yellow)%h'
    author='%C(auto,cyan)Author: %>(15,trunc)%aN %<(25,trunc)%ae %as'
    committer='%C(auto,green)Committer: %>(15,trunc)%cN %<(25,trunc)%ce %cs'
    message='%C(auto)%s %d'
    git log --pretty="format: $hash$divider$author$divider$committer$divider$message" "$@"
)

poi() (
    echo "> log -10"
    log -10

    echo
    echo "> git branch"
    git branch

    echo
    echo "> git status"
    git status
)

diffc() (
    git diff --cached "$@"
)

amend() (
    git status
    git commit -a --amend
)

commit_detail() (
    commit_id="$1"
    if [ -z "$commit_id" ]; then
        commit_id="HEAD"
    fi

    color1="%C(auto,cyan)"
    color2="%C(auto,reset)"

    general_format="General:
    $color1%%d  - ref names    $color2 - %d
    $color1%%s  - subject      $color2 - %s
    $color1%%H  - hash         $color2 - %H
    "

    author_format="Author:
    $color1%%an - name         $color2 - %an
    $color1%%ae - email        $color2 - %ae
    $color1%%aD - date RFC2822 $color2 - %aD
    "

    committer_format="Committer:
    $color1%%cn - name         $color2 - %cn
    $color1%%ce - email        $color2 - %ce
    $color1%%cD - date RFC2822 $color2 - %cD
    "

    git log --pretty="format:$general_format" "$commit_id" -1
    git log --pretty="format:$author_format" "$commit_id" -1
    git log --pretty="format:$committer_format" "$commit_id" -1
)
